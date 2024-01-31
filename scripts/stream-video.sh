#!/bin/sh

if [ -z "$DATA_PATH" ]; then
  echo '$DATA_PATH is empty'
  exit 1
fi

if [ -z "$STREAM_SERVER" ]; then
  echo '$STREAM_SERVER is empty'
  exit 1
fi

if [ ! -f "data/video-1.mp4" ]; then
  echo "Baixando vídeo de teste"
  mkdir -p data
  curl 'https://www.pexels.com/download/video/19015559/?fps=29.97&h=1080&w=1920' -L -o ${DATA_PATH}/video-1.mp4
else
  echo "Vídeo de teste já existe"
fi

ffmpeg -re -stream_loop -1 -i ${DATA_PATH}/video-1.mp4 -vcodec libx264 -f rtsp rtsp://${STREAM_SERVER}:8554/video-1&
ffmpeg -re -stream_loop -1 -i ${DATA_PATH}/video-1.mp4 -vcodec libx265 -f rtsp rtsp://${STREAM_SERVER}:8554/video-2&
wait
