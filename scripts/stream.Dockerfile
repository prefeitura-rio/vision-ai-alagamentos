FROM alpine:latest

RUN apk add ffmpeg curl

COPY ./stream-video.sh /stream-video.sh
RUN chmod +x /stream-video.sh

ENV DATA_PATH=/data

ENTRYPOINT ["/stream-video.sh"]
