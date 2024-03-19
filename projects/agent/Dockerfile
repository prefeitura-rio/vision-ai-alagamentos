FROM golang:1.22-bookworm AS builder
WORKDIR /usr/src/app

RUN apt update
RUN apt install -y libavcodec-dev libavutil-dev libswscale-dev

COPY go.mod go.sum ./
COPY libs libs
RUN echo 'replace github.com/prefeitura-rio/vision-ai/libs v0.0.0 => ./libs' >> go.mod
RUN go mod download && go mod verify

COPY *.go ./
RUN go build -o /usr/src/app/bin .

FROM debian:12
WORKDIR /usr/src/app

RUN apt update
RUN apt install -y libswscale6 libavcodec59 libavutil57 ca-certificates

COPY --from=builder /usr/src/app/bin /usr/src/app/bin

ENTRYPOINT ["/usr/src/app/bin"]
