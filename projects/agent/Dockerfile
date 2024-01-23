FROM ghcr.io/hybridgroup/opencv:4.8.1 as build

WORKDIR /usr/src/app

COPY go.mod go.sum ./
RUN go mod download && go mod verify

COPY *.go .
RUN go build -v -o /usr/local/bin/app ./...

ENTRYPOINT ["/usr/local/bin/app"]
