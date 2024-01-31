package main

import (
	"context"
	"errors"
	"fmt"
	"image"
	"log"
	"strings"
	"time"

	"github.com/bluenviron/gortsplib/v4"
	"github.com/bluenviron/gortsplib/v4/pkg/base"
	"github.com/bluenviron/gortsplib/v4/pkg/description"
	"github.com/bluenviron/gortsplib/v4/pkg/format"
	"github.com/bluenviron/gortsplib/v4/pkg/format/rtph264"
	"github.com/bluenviron/gortsplib/v4/pkg/format/rtph265"
	"github.com/pion/rtp"
)

type CameraAPI struct {
	ID             string `json:"id"`
	RTSP_URL       string `json:"rtsp_url"`
	UpdateInterval int    `json:"update_interval"`
}

type Camera struct {
	id             string
	getURL         *base.URL
	snapshotURL    string
	updateInterval time.Duration
	client         *gortsplib.Client
	decoders       *decoders
}

func NewCamera(api CameraAPI, cameraBaseURL string) (*Camera, error) {
	u, err := base.ParseURL(api.RTSP_URL)
	if err != nil {
		return nil, fmt.Errorf("error parsing RTSP URL: %w", err)
	}

	if api.UpdateInterval <= 0 {
		return nil, fmt.Errorf("update interval must be greater than zero")
	}

	return &Camera{
		id:             api.ID,
		getURL:         u,
		snapshotURL:    fmt.Sprintf("%s/%s/snapshot", cameraBaseURL, api.ID),
		updateInterval: time.Duration(api.UpdateInterval) * time.Second,
		client: &gortsplib.Client{
			ReadTimeout: time.Duration(api.UpdateInterval) * time.Second / 2,
		},
	}, nil
}

func (camera *Camera) setDecoders() error {
	desc, _, err := camera.client.Describe(camera.getURL)
	if err != nil {
		return fmt.Errorf("error describing camera: %w", err)
	}

	medias := []*description.Media{}
	rtpDecoders := map[string]rtpDecoder{}
	frameDecoders := map[string]frameDecoder{}

	var h265 *format.H265
	var h264 *format.H264

	media264 := desc.FindFormat(&h264)
	if media264 != nil {
		rtpDecoder, err := h264.CreateDecoder()
		if err != nil {
			return fmt.Errorf("error creating H264 decoder: %w", err)
		}

		frameDecoder := &h264Decoder{}
		err = frameDecoder.initialize()
		if err != nil {
			return fmt.Errorf("error initializing decoder: %w", err)
		}

		if h264.SPS != nil {
			_, err = frameDecoder.decode(h264.SPS)
			if err != nil {
				return fmt.Errorf("error setting H264 SPS: %w", err)
			}
		}
		if h264.PPS != nil {
			_, err = frameDecoder.decode(h264.PPS)
			if err != nil {
				return fmt.Errorf("error setting H264 PPS: %w", err)
			}
		}

		medias = append(medias, media264)
		rtpDecoders["H264"] = rtpDecoder
		frameDecoders["H264"] = frameDecoder
	}

	media265 := desc.FindFormat(&h265)
	if media265 != nil {
		rtpDecoder, err := h265.CreateDecoder()
		if err != nil {
			return fmt.Errorf("error creating H265 decoder: %w", err)
		}

		frameDecoder := &h265Decoder{}
		err = frameDecoder.initialize()
		if err != nil {
			return fmt.Errorf("error initializing H265 decoder: %w", err)
		}

		if h265.VPS != nil {
			_, err = frameDecoder.decode(h265.VPS)
			if err != nil {
				return fmt.Errorf("error setting H265 VPS: %w", err)
			}
		}
		if h265.SPS != nil {
			_, err = frameDecoder.decode(h265.SPS)
			if err != nil {
				return fmt.Errorf("error setting H265 SPS: %w", err)
			}
		}
		if h265.PPS != nil {
			_, err = frameDecoder.decode(h265.PPS)
			if err != nil {
				return fmt.Errorf("error setting H265 PPS: %w", err)
			}
		}

		medias = append(medias, media265)
		rtpDecoders["H265"] = rtpDecoder
		frameDecoders["H265"] = frameDecoder
	}

	if len(medias) == 0 {
		return errMediaNotFound
	}

	err = camera.client.SetupAll(desc.BaseURL, medias)
	if err != nil {
		return fmt.Errorf("error setuping medias: %w", err)
	}

	camera.decoders = &decoders{
		rtp:   rtpDecoders,
		frame: frameDecoders,
	}

	return nil
}

func (camera *Camera) closeDecoders() {
	for _, decoder := range camera.decoders.frame {
		decoder.close()
	}
}

func (camera *Camera) start() error {
	err := camera.client.Start(camera.getURL.Scheme, camera.getURL.Host)
	if err != nil {
		return fmt.Errorf("error connecting to the server: %w", err)
	}

	err = camera.setDecoders()
	if err != nil {
		return fmt.Errorf("error set decoders: %w", err)
	}

	return nil
}

func (camera *Camera) close() {
	camera.closeDecoders()
	camera.client.Close()
}

func (camera *Camera) getNextFrame(ctx context.Context) (image.Image, bool, error) {
	imgch := make(chan image.Image)

	camera.client.OnPacketRTPAny(func(m *description.Media, f format.Format, pkt *rtp.Packet) {
		defer func() {
			if r := recover(); r != nil {
				message := fmt.Sprintf("%s", r)
				if !strings.Contains(message, "send on closed channel") {
					panic(r)
				}
			}
		}()
		_, ok := camera.client.PacketPTS(m, pkt)
		if !ok {
			return
		}

		validErrs := []error{
			rtph264.ErrMorePacketsNeeded,
			rtph264.ErrNonStartingPacketAndNoPrevious,
			rtph265.ErrMorePacketsNeeded,
			rtph265.ErrNonStartingPacketAndNoPrevious,
			errAllFrameEmpty,
		}

		validErrsMessags := []string{
			"invalid fragmentation unit (non-starting)",
		}

		img, err := decodeRTPPacket(f, pkt, camera.decoders)
		if err != nil {
			for _, validErr := range validErrs {
				if errors.Is(err, validErr) {
					return
				}
			}

			for _, validMessage := range validErrsMessags {
				if strings.Contains(err.Error(), validMessage) {
					return
				}
			}

			log.Printf("error deconding package: %s", err)
		} else {
			imgch <- img
		}
	})

	_, err := camera.client.Play(nil)
	if err != nil {
		return nil, false, fmt.Errorf("error playing stream: %w", err)
	}

	select {
	case <-ctx.Done():
		camera.client.OnPacketRTPAny(func(m *description.Media, f format.Format, p *rtp.Packet) {})
		close(imgch)
		_, err := camera.client.Pause()
		if err != nil {
			return nil, false, fmt.Errorf("multiples errs: %w", errors.Join(ctx.Err(), err))
		}
		return nil, false, ctx.Err()
	case img := <-imgch:
		camera.client.OnPacketRTPAny(func(m *description.Media, f format.Format, p *rtp.Packet) {})
		close(imgch)
		_, err := camera.client.Pause()
		if err != nil {
			return img, true, fmt.Errorf("error pausing client: %s", err)
		}
		return img, true, nil
	}
}
