#!/bin/sh
set -eu

DIR="${1:-/volume1/docker/homeassistant/www/lawn-timelapse}"
FPS="${FPS:-12}"
WIDTH="${WIDTH:-1080}"
HEIGHT="${HEIGHT:-1920}"
OUTPUT_BASENAME="${OUTPUT_BASENAME:-lawn-timelapse}"
TIME_FILTER="${TIME_FILTER:-}"
SMOOTH="${SMOOTH:-0}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ -n "$TIME_FILTER" ]; then
  snapshot_name="rear_lawn_*_${TIME_FILTER}.jpg"
else
  snapshot_name="rear_lawn_*.jpg"
fi

count="$(find "$DIR" -maxdepth 1 -type f -name "$snapshot_name" | wc -l | tr -d ' ')"
if [ "$count" -lt 2 ]; then
  echo "Need at least 2 $snapshot_name snapshots in $DIR; found $count." >&2
  exit 1
fi

i=0
find "$DIR" -maxdepth 1 -type f -name "$snapshot_name" | sort | while IFS= read -r file; do
  ln -s "$file" "$TMP/frame$(printf '%06d' "$i").jpg"
  i=$((i + 1))
done

if ffmpeg -hide_banner -encoders 2>/dev/null | grep -q 'libx264'; then
  ext=mp4
  codec_args="-c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p"
elif ffmpeg -hide_banner -encoders 2>/dev/null | grep -q ' mpeg4 '; then
  ext=mp4
  codec_args="-c:v mpeg4 -q:v 4 -pix_fmt yuv420p"
else
  ext=avi
  codec_args="-c:v mjpeg -q:v 3"
fi

stamp="$(date +%Y%m%d-%H%M%S)"
out="$DIR/$OUTPUT_BASENAME-$stamp.$ext"
latest="$DIR/$OUTPUT_BASENAME-latest.$ext"
video_filter="scale=$WIDTH:$HEIGHT:force_original_aspect_ratio=decrease,pad=$WIDTH:$HEIGHT:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
if [ "$SMOOTH" = "1" ]; then
  video_filter="deflicker=mode=pm:size=5,eq=gamma=1.08:contrast=0.96:saturation=1.03,$video_filter"
fi

if ! ffmpeg -hide_banner -y \
  -framerate "$FPS" \
  -i "$TMP/frame%06d.jpg" \
  -vf "$video_filter" \
  $codec_args \
  "$out"; then
  out="$DIR/$OUTPUT_BASENAME-$stamp.avi"
  latest="$DIR/$OUTPUT_BASENAME-latest.avi"
  ffmpeg -hide_banner -y \
    -framerate "$FPS" \
    -i "$TMP/frame%06d.jpg" \
    -vf "$video_filter" \
    -c:v mjpeg \
    -q:v 3 \
    "$out"
fi

cp "$out" "$latest"
echo "Rendered $count snapshots to $out"
echo "Latest copy: $latest"
