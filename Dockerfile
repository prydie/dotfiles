FROM ubuntu:16.10
MAINTAINER Andrew Pryde <andrew@>

RUN locale-gen en_GB.UTF-8

RUN apt-get update -qq && \
    apt-get install -qq \
      autoconf \
      build-essential \
      curl \
      git \
      openssl \
      python \
      python-pip \
      sudo \
      tmux \
      nodejs \
    && apt-get clean

RUN curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
RUN apt-get install -qq \
      nodejs \
    && apt-get clean


RUN useradd -s /bin/bash tester

ADD . /home/tester/.dotfiles
RUN chown -R tester:tester /home/tester && \
    echo 'tester ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/tester && \
    chmod 0440 /etc/sudoers.d/tester
USER tester

ENV HOME /home/tester
ENV LOGNAME tester
ENV PATH /home/tester/.local/bin:$PATH

WORKDIR /home/tester/.dotfiles
RUN ./install.sh -y
