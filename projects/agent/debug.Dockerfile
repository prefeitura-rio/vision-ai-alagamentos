FROM golang:1.22-bookworm AS builder
WORKDIR /usr/src/app

RUN apt-get update

RUN apt-get -y install \
  autoconf \
  automake \
  build-essential \
  cmake \
  git-core \
  libass-dev \
  libfreetype6-dev \
  libgnutls28-dev \
  libmp3lame-dev \
  libsdl2-dev \
  libtool \
  libva-dev \
  libvdpau-dev \
  libvorbis-dev \
  libxcb1-dev \
  libxcb-shm0-dev \
  libxcb-xfixes0-dev \
  meson \
  ninja-build \
  pkg-config \
  texinfo \
  wget \
  yasm \
  zlib1g-dev \
  libunistring-dev \
  libaom-dev \
  libdav1d-dev \
  nasm \
  libx264-dev \
  libx265-dev \
  libnuma-dev

RUN mkdir -p /ffmpeg/sources /ffmpeg/bin

ENV PATH="/ffmpeg/bin:$PATH" \
    PKG_CONFIG_PATH="/ffmpeg/build/lib/pkgconfig:$PKG_CONFIG_PATH"

RUN cd /ffmpeg/sources && \
   wget -O ffmpeg-snapshot.tar.bz2 https://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2 && \
   tar xjvf ffmpeg-snapshot.tar.bz2 && \
   cd ffmpeg && \
   ./configure \
     --prefix="/ffmpeg/build" \
     --pkg-config-flags="--static" \
     --extra-cflags="-I/ffmpeg/build/include -g" \
     --extra-ldflags="-L/ffmpeg/build/lib -g" \
     --extra-libs="-lpthread -lm" \
     --ld="g++" \
     --bindir="/ffmpeg/bin" \
     --enable-gpl \
     --enable-gnutls \
     --enable-libass \
     --enable-libfreetype \
     --enable-libmp3lame \
     --enable-libvorbis \
     --enable-libx264 \
     --enable-libx265 \
     --enable-nonfree \
     --disable-optimizations && \
   make && \
   make install && \
   hash -r

COPY libs ../../
COPY go.mod go.sum ./
RUN go mod download && go mod verify

COPY *.go ./
RUN go build -o /usr/src/app/bin .

ENTRYPOINT ["/usr/src/app/bin"]
