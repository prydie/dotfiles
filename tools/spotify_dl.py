import asyncio
import argparse
import json
import os
import re
import ssl
import time
from pathlib import Path

import aiohttp
import websockets
from music_assistant_client import MusicAssistantClient
from music_assistant_client.exceptions import InvalidState
from mutagen.id3 import APIC, TALB, TCOP, TDRC, TIT2, TPE1, TPE2, TPOS, TPUB, TRCK, TSRC, ID3
from mutagen.mp3 import MP3
from websockets.exceptions import ConnectionClosed

MA_API_URL = "https://music.nas.prydie.co.uk"
SENDSPIN_WS_URL = "wss://music.nas.prydie.co.uk/sendspin"

DEFAULT_PLAYER_ID = "ma_hq_ripper_v11"
STREAM_FORMAT = {"codec": "pcm", "sample_rate": 48000, "channels": 2, "bit_depth": 16}
SENDSPIN_HEADER_BYTES = 9


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    raise SystemExit(
        f"Missing required environment variable: {name}\n"
        f"Run with `{name}=... {os.path.basename(__file__)}`."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Spotify items through Music Assistant SendSpin.")
    parser.add_argument(
        "--playlist",
        action="append",
        default=[],
        help="Music Assistant playlist URI to download. Repeat to download multiple playlists.",
    )
    parser.add_argument(
        "--track",
        action="append",
        default=[],
        help="Music Assistant track URI to download. Repeat to download multiple tracks.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=".",
        help="Directory to write output files to. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--player-id",
        default=DEFAULT_PLAYER_ID,
        help=f"SendSpin player ID to create and use. Defaults to {DEFAULT_PLAYER_ID}.",
    )
    parser.add_argument(
        "--keep-player-config",
        action="store_true",
        help="Keep the Music Assistant player config after the run. By default, non-default player IDs are cleaned up.",
    )
    parser.add_argument(
        "--cleanup-player-prefix",
        action="append",
        default=[],
        help="Remove Music Assistant player configs whose player_id starts with this prefix. Repeat to remove multiple prefixes.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of resolved tracks to process.",
    )
    parser.add_argument(
        "--one-track",
        action="store_true",
        help="Process only the first resolved track.",
    )
    args = parser.parse_args()
    if not args.playlist and not args.track and not args.cleanup_player_prefix:
        parser.error("provide at least one --playlist or --track")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be >= 1")
    return args


def safe_track_name(track) -> str:
    def clean_part(value: str | None) -> str:
        text = (value or "").strip()
        text = re.sub(
            r"\.(mp3|aac|pcm|raw|flac|m4a|ogg|opus|wav)\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r'[\\/\0<>:"|?*]+', "-", text)
        text = re.sub(r"\s+", " ", text).strip().strip(".")
        return text

    artist = clean_part(track.artists[0].name if track.artists else "Unknown")
    title = clean_part(track.name)
    name = f"{artist or 'Unknown'} - {title or 'Unknown Track'}"
    return name or "Unknown Track"


def unique_output_paths(output_dir: Path, base_name: str) -> tuple[Path, Path]:
    candidate = base_name
    index = 2
    while True:
        final_mp3 = output_dir / f"{candidate}.mp3"
        temp_pcm = output_dir / f"{candidate}.pcm"
        if not final_mp3.exists() and temp_pcm.exists() and temp_pcm.stat().st_size == 0:
            temp_pcm.unlink()
        if not final_mp3.exists() and not temp_pcm.exists():
            return final_mp3, temp_pcm
        if final_mp3.exists():
            return final_mp3, temp_pcm
        candidate = f"{base_name} ({index})"
        index += 1


def first_external_id(track, key: str) -> str | None:
    for ext_key, ext_value in getattr(track, "external_ids", []) or []:
        if ext_key == key and ext_value:
            return ext_value
    return None


def release_year(track) -> str | None:
    album = getattr(track, "album", None)
    if album and getattr(album, "year", None):
        return str(album.year)
    metadata = getattr(track, "metadata", None)
    if metadata and getattr(metadata, "release_date", None):
        return str(metadata.release_date)[:4]
    if album and getattr(album, "metadata", None) and getattr(album.metadata, "release_date", None):
        return str(album.metadata.release_date)[:4]
    return None


def artwork_url(track) -> str | None:
    for container in (getattr(track, "metadata", None), getattr(getattr(track, "album", None), "metadata", None)):
        if not container:
            continue
        for image in getattr(container, "images", []) or []:
            path = getattr(image, "path", None)
            if path:
                return path
    return None


async def write_mp3_metadata(session: aiohttp.ClientSession, mp3_path: Path, track) -> None:
    """Write Music Assistant metadata into an MP3, including artwork when available."""
    tags = ID3(mp3_path) if mp3_path.exists() else ID3()
    tags.delall("TIT2")
    tags.delall("TPE1")
    tags.delall("TPE2")
    tags.delall("TALB")
    tags.delall("TRCK")
    tags.delall("TPOS")
    tags.delall("TDRC")
    tags.delall("TSRC")
    tags.delall("TPUB")
    tags.delall("TCOP")
    tags.delall("APIC")

    title = getattr(track, "name", None)
    if title:
        tags.add(TIT2(encoding=3, text=title))

    artists = [artist.name for artist in getattr(track, "artists", []) or [] if getattr(artist, "name", None)]
    if artists:
        tags.add(TPE1(encoding=3, text=artists))
        tags.add(TPE2(encoding=3, text=artists[0]))

    album = getattr(track, "album", None)
    if album and getattr(album, "name", None):
        tags.add(TALB(encoding=3, text=album.name))

    if getattr(track, "track_number", None):
        tags.add(TRCK(encoding=3, text=str(track.track_number)))
    if getattr(track, "disc_number", None):
        tags.add(TPOS(encoding=3, text=str(track.disc_number)))
    if year := release_year(track):
        tags.add(TDRC(encoding=3, text=year))
    if isrc := first_external_id(track, "isrc"):
        tags.add(TSRC(encoding=3, text=isrc))
    if album and getattr(album, "metadata", None):
        if getattr(album.metadata, "label", None):
            tags.add(TPUB(encoding=3, text=album.metadata.label))
        if getattr(album.metadata, "copyright", None):
            tags.add(TCOP(encoding=3, text=album.metadata.copyright))

    if cover_url := artwork_url(track):
        try:
            async with session.get(cover_url) as response:
                if response.ok:
                    cover_bytes = await response.read()
                    mime = response.headers.get("Content-Type", "image/jpeg")
                    tags.add(
                        APIC(
                            encoding=3,
                            mime=mime,
                            type=3,
                            desc="Cover",
                            data=cover_bytes,
                        )
                    )
        except Exception:
            pass

    tags.save(mp3_path, v2_version=3)
    MP3(mp3_path)


async def resolve_tracks(ma_client: MusicAssistantClient, playlist_uris: list[str], track_uris: list[str]):
    tracks = []
    for playlist_uri in playlist_uris:
        playlist = await ma_client.music.get_item_by_uri(playlist_uri)
        playlist_tracks = await ma_client.music.get_playlist_tracks(playlist.item_id, playlist.provider)
        tracks.extend(playlist_tracks)
    for track_uri in track_uris:
        tracks.append(await ma_client.music.get_item_by_uri(track_uri))
    return tracks


async def heartbeat(ws):
    """Keep the server from hanging up by syncing time every 5 seconds."""
    while True:
        try:
            await ws.send(json.dumps({"type": "client/time", "payload": {"client_transmitted": int(time.time() * 1000)}}))
            await asyncio.sleep(5)
        except Exception:
            break


async def open_sendspin_ws(ssl_ctx, token: str, player_id: str):
    ws = await websockets.connect(
        f"{SENDSPIN_WS_URL}?player_id={player_id}",
        ssl=ssl_ctx,
    )
    await ws.send(json.dumps({"type": "auth", "token": token, "client_id": player_id}))
    auth_reply = json.loads(await ws.recv())
    if auth_reply.get("type") != "auth_ok":
        raise RuntimeError(f"SendSpin auth failed: {auth_reply!r}")

    await ws.send(json.dumps({"type": "client/hello", "payload": {
        "client_id": player_id, "name": player_id, "version": 1,
        "supported_roles": ["player@v1"],
        "player@v1_support": {
            "supported_formats": [STREAM_FORMAT],
            "buffer_capacity": 262144,
            "supported_commands": [],
        },
    }}))
    server_hello = json.loads(await ws.recv())
    if server_hello.get("type") != "server/hello":
        raise RuntimeError(f"Unexpected SendSpin hello: {server_hello!r}")

    await ws.send(json.dumps({
        "type": "client/state",
        "payload": {"state": "synchronized", "player": {"static_delay_ms": 0}},
    }))
    return ws


async def wait_for_player(ma_client: MusicAssistantClient, queue_id: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        players = await send_mass_command(ma_client, "players/all")
        player = next((item for item in players if item["player_id"] == queue_id), None)
        if player and player.get("available"):
            return
        await asyncio.sleep(0.25)
    raise TimeoutError(f"Player {queue_id} did not become available")


async def ensure_mass_connection(ma_client: MusicAssistantClient) -> None:
    if ma_client.connection.connected:
        return
    await ma_client.connect()


async def reset_mass_connection(ma_client: MusicAssistantClient) -> None:
    try:
        await ma_client.disconnect()
    except Exception:
        pass
    await ma_client.connect()


async def send_mass_command(ma_client: MusicAssistantClient, command: str, **kwargs):
    try:
        await ensure_mass_connection(ma_client)
        return await ma_client.send_command(command, **kwargs)
    except InvalidState:
        await reset_mass_connection(ma_client)
        return await ma_client.send_command(command, **kwargs)


async def cleanup_player_config(ma_client: MusicAssistantClient, player_ids: list[str]) -> None:
    """Remove stale Music Assistant player configs for transient downloader players."""
    for player_id in player_ids:
        try:
            await ma_client.config.remove_player_config(player_id)
            print(f"🧹 Removed Music Assistant player config: {player_id}")
        except Exception as err:
            print(f"⚠️ Could not remove Music Assistant player config {player_id}: {err}")


async def cleanup_player_prefixes(prefixes: list[str]) -> None:
    """Remove stale Music Assistant player configs matching the given prefixes."""
    token = require_env("MUSIC_ASSISTANT_TOKEN")
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    normalized_prefixes = [prefix.strip() for prefix in prefixes if prefix.strip()]
    if not normalized_prefixes:
        print("⚠️ No cleanup prefixes provided.")
        return

    async with aiohttp.ClientSession() as session:
        async with MusicAssistantClient(MA_API_URL, session, token=token, ssl_context=ssl_ctx) as ma_client:
            player_configs = await ma_client.config.get_player_configs()
            matched_ids = sorted(
                {
                    player_config.player_id
                    for player_config in player_configs
                    if any(player_config.player_id.startswith(prefix) for prefix in normalized_prefixes)
                }
            )
            if not matched_ids:
                print(
                    "⚠️ No Music Assistant player configs matched: "
                    + ", ".join(normalized_prefixes)
                )
                return
            print(f"🧹 Removing {len(matched_ids)} Music Assistant player configs...")
            await cleanup_player_config(ma_client, matched_ids)


async def download_via_sendspin(
    playlist_uris: list[str],
    track_uris: list[str],
    output_dir: Path,
    player_id: str,
    limit: int | None,
    keep_player_config: bool,
):
    token = require_env("MUSIC_ASSISTANT_TOKEN")
    output_dir.mkdir(parents=True, exist_ok=True)
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    queue_id = f"up{player_id}"

    async with aiohttp.ClientSession() as session:
        async with MusicAssistantClient(MA_API_URL, session, token=token, ssl_context=ssl_ctx) as ma_client:
            tracks = await resolve_tracks(ma_client, playlist_uris, track_uris)
            if limit is not None:
                tracks = tracks[:limit]
            print(f"🔗 Connected. Tracks: {len(tracks)}")
            print(f"✅ Creating SendSpin player '{player_id}'.")
            try:
                for i, track in enumerate(tracks):
                    safe_name = safe_track_name(track)
                    final_mp3, temp_pcm = unique_output_paths(output_dir, safe_name)

                    if final_mp3.exists():
                        if temp_pcm.exists():
                            temp_pcm.unlink()
                        await write_mp3_metadata(session, final_mp3, track)
                        print(f"\n⏭️ [{i+1}/{len(tracks)}] Skipping existing MP3: {safe_name}")
                        continue

                    print(f"\n📥 [{i+1}/{len(tracks)}] Harvesting: {safe_name}")

                    bytes_written = 0
                    async with await open_sendspin_ws(ssl_ctx, token, player_id) as ws:
                        await wait_for_player(ma_client, queue_id)
                        await send_mass_command(
                            ma_client,
                            "players/cmd/power",
                            player_id=queue_id,
                            powered=True,
                        )
                        await send_mass_command(
                            ma_client,
                            "player_queues/play_media",
                            queue_id=queue_id,
                            media=track.uri,
                        )

                        heartbeat_task = asyncio.create_task(heartbeat(ws))
                        try:
                            with temp_pcm.open("wb") as f:
                                capture_started = time.time()
                                last_active = time.time()
                                while True:
                                    try:
                                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                                        if isinstance(msg, bytes):
                                            payload = msg[SENDSPIN_HEADER_BYTES:]
                                            f.write(payload)
                                            bytes_written += len(payload)
                                            last_active = time.time()
                                            print(f"   💾 {bytes_written // 1024} KB...", end="\r")
                                            continue

                                        data = json.loads(msg)
                                        msg_type = data.get("type")
                                        if msg_type == "server/time":
                                            await ws.send(json.dumps({
                                                "type": "client/time",
                                                "payload": {"client_transmitted": int(time.time() * 1000)},
                                            }))
                                        elif msg_type == "stream/start":
                                            last_active = time.time()
                                        elif msg_type == "stream/request-format":
                                            await ws.send(json.dumps({
                                                "type": "stream/request-format",
                                                "payload": {"format": STREAM_FORMAT},
                                            }))
                                        elif msg_type == "stream/stop":
                                            break
                                        elif (
                                            msg_type == "group/update"
                                            and data.get("payload", {}).get("playback_state") == "stopped"
                                        ):
                                            if bytes_written > 100000:
                                                break
                                            if (time.time() - capture_started) > 5.0:
                                                break
                                    except asyncio.TimeoutError:
                                        if bytes_written == 0 and (time.time() - capture_started) > 20.0:
                                            break
                                        if bytes_written > 100000 and (time.time() - last_active) > 8.0:
                                            break
                                        continue
                                    except ConnectionClosed:
                                        break
                        finally:
                            heartbeat_task.cancel()

                    if bytes_written > 1000:
                        print("\n✅ Captured. Converting...")
                        temp_mp3 = final_mp3.with_suffix(".part.mp3")
                        if temp_mp3.exists():
                            temp_mp3.unlink()
                        proc = await asyncio.create_subprocess_exec(
                            "ffmpeg",
                            "-y",
                            "-f", "s16le",
                            "-ar", str(STREAM_FORMAT["sample_rate"]),
                            "-ac", str(STREAM_FORMAT["channels"]),
                            "-i", str(temp_pcm),
                            "-codec:a", "libmp3lame",
                            "-b:a", "320k",
                            "-f", "mp3",
                            str(temp_mp3),
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        _, stderr = await proc.communicate()
                        return_code = proc.returncode
                        if return_code != 0:
                            if temp_mp3.exists():
                                temp_mp3.unlink()
                            ffmpeg_error = (stderr or b"").decode("utf-8", errors="replace").strip()
                            error_suffix = f": {ffmpeg_error}" if ffmpeg_error else ""
                            raise RuntimeError(
                                f"ffmpeg conversion failed for {safe_name}; kept PCM at {temp_pcm}{error_suffix}"
                            )
                        if temp_pcm.exists():
                            temp_pcm.unlink()
                        temp_mp3.replace(final_mp3)
                        await write_mp3_metadata(session, final_mp3, track)
                    else:
                        print("\n⚠️ No audio bytes received.")
                        if temp_pcm.exists():
                            temp_pcm.unlink()
            finally:
                if player_id != DEFAULT_PLAYER_ID and not keep_player_config:
                    await cleanup_player_config(ma_client, [queue_id, player_id])

if __name__ == "__main__":
    try:
        args = parse_args()
        if args.cleanup_player_prefix:
            asyncio.run(
                cleanup_player_prefixes(args.cleanup_player_prefix)
            )
        else:
            asyncio.run(
                download_via_sendspin(
                    playlist_uris=args.playlist,
                    track_uris=args.track,
                    output_dir=Path(args.output_dir).expanduser().resolve(),
                    player_id=args.player_id,
                    limit=1 if args.one_track else args.limit,
                    keep_player_config=args.keep_player_config,
                )
            )
    except KeyboardInterrupt:
        print("\n🛑 Stopped.")
