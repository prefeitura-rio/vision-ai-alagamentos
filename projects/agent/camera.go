package main

import (
	"context"
	"errors"
	"fmt"
	"image"
	"log"
	"slices"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/bluenviron/gortsplib/v4"
	"github.com/bluenviron/gortsplib/v4/pkg/base"
	"github.com/bluenviron/gortsplib/v4/pkg/description"
	"github.com/bluenviron/gortsplib/v4/pkg/format"
	"github.com/bluenviron/gortsplib/v4/pkg/format/rtph264"
	"github.com/bluenviron/gortsplib/v4/pkg/format/rtph265"
	"github.com/pion/rtp"
)

var (
	ErrGetFrameTimeout error = fmt.Errorf("timeout on getting frame")
	ErrMediaNotFound   error = fmt.Errorf("media not found")
)

type CameraAPI struct {
	ID             string `json:"id"`
	RTSP_URL       string `json:"rtsp_url"`
	UpdateInterval int    `json:"update_interval"`
	snapshotURL    string
	accessToken    *AccessToken
}

type Camera struct {
	id             string
	getURL         *base.URL
	updateInterval time.Duration
	client         *gortsplib.Client
	decoders       *decoders
	accessToken    *AccessToken
}

func NewCamera(api CameraAPI) (*Camera, error) {
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
		updateInterval: time.Duration(api.UpdateInterval) * time.Second,
		accessToken:    api.accessToken,
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
		return ErrMediaNotFound
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

func (camera *Camera) getNextFrame() (image.Image, error) {
	imgch := make(chan image.Image)
	decoded := false
	mu := sync.Mutex{}

	camera.client.OnPacketRTPAny(func(m *description.Media, f format.Format, pkt *rtp.Packet) {
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

		mu.Lock()
		defer mu.Unlock()

		if decoded {
			return
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
			decoded = true
		}
	})

	_, err := camera.client.Play(nil)
	if err != nil {
		return nil, fmt.Errorf("error playing stream: %w", err)
	}

	tick := time.NewTicker(camera.updateInterval / 2)
	defer tick.Stop()

	select {
	case <-tick.C:
		camera.client.OnPacketRTPAny(func(m *description.Media, f format.Format, p *rtp.Packet) {})
		close(imgch)

		_, err := camera.client.Pause()
		if err != nil {
			return nil, fmt.Errorf("multiples errs: %w", errors.Join(ErrGetFrameTimeout, err))
		}

		return nil, ErrGetFrameTimeout
	case img := <-imgch:
		camera.client.OnPacketRTPAny(func(m *description.Media, f format.Format, p *rtp.Packet) {})
		close(imgch)

		_, err := camera.client.Pause()
		if err != nil {
			return nil, fmt.Errorf("error pausing client: %s", err)
		}

		return img, nil
	}
}

type camerasByUpdateInterval struct {
	ids            []string
	cameras        map[int][]CameraAPI
	intervals      []int
	queue          chan CameraAPI
	mutex          *sync.RWMutex
	startedQueue   atomic.Bool
	ctxStart       context.Context
	cancelStart    context.CancelFunc
	wgStart        *sync.WaitGroup
	consumingQueue atomic.Bool
	ctxConsume     context.Context
	cancelConsume  context.CancelFunc
	wgConsume      *sync.WaitGroup
}

func newCamerasByUpdateInterval(queueBuffer int) *camerasByUpdateInterval {
	return &camerasByUpdateInterval{
		ids:            []string{},
		cameras:        map[int][]CameraAPI{},
		intervals:      []int{},
		queue:          make(chan CameraAPI, queueBuffer),
		mutex:          &sync.RWMutex{},
		startedQueue:   atomic.Bool{},
		ctxStart:       context.Background(),
		cancelStart:    func() {},
		wgStart:        &sync.WaitGroup{},
		consumingQueue: atomic.Bool{},
		ctxConsume:     context.Background(),
		cancelConsume:  func() {},
		wgConsume:      &sync.WaitGroup{},
	}
}

func (c *camerasByUpdateInterval) Replace(cameras []CameraAPI) {
	c.mutex.Lock()
	defer c.mutex.Unlock()

	c.cameras = map[int][]CameraAPI{}
	c.ids = []string{}
	c.intervals = []int{}

	for _, camera := range cameras {
		if slices.Contains(c.ids, camera.ID) {
			continue
		}

		c.ids = append(c.ids, camera.ID)
		interval := camera.UpdateInterval

		if slices.Contains(c.intervals, interval) {
			c.cameras[interval] = append(c.cameras[interval], camera)
		} else {
			c.cameras[interval] = []CameraAPI{camera}
			c.intervals = append(c.intervals, interval)
		}
	}
}

func (c *camerasByUpdateInterval) Equals(camerasAPI []CameraAPI) bool {
	c.mutex.RLock()
	defer c.mutex.RUnlock()

	if len(camerasAPI) != len(c.ids) {
		return false
	}

	ids := []string{}

	for _, camera := range camerasAPI {
		if !slices.Contains(c.ids, camera.ID) {
			return false
		}

		if slices.Contains(ids, camera.ID) {
			continue
		}

		cameras, ok := c.cameras[camera.UpdateInterval]
		if !ok {
			return false
		}

		if !slices.ContainsFunc(cameras, func(ca CameraAPI) bool { return ca.ID == camera.ID }) {
			return false
		}

		ids = append(ids, camera.ID)
	}

	return len(ids) == len(c.ids)
}

func (c *camerasByUpdateInterval) Len() int {
	c.mutex.RLock()
	defer c.mutex.RUnlock()

	return len(c.ids)
}

func (c *camerasByUpdateInterval) StartQueue(ctx context.Context) error {
	if !c.startedQueue.CompareAndSwap(false, true) {
		return fmt.Errorf("queue already started")
	}

	ctx, cancel := context.WithCancel(ctx)
	c.ctxStart = ctx
	c.cancelStart = cancel

	c.mutex.RLock()
	defer c.mutex.RUnlock()

	c.wgStart.Add(len(c.intervals))

	for _, updateInterval := range c.intervals {
		updateInterval := updateInterval

		go func() {
			defer c.wgStart.Done()

			interval := time.Duration(updateInterval) * time.Second

			for {
				c.mutex.RLock()
				for _, camera := range c.cameras[updateInterval] {
					c.queue <- camera
				}
				c.mutex.RUnlock()

				select {
				case <-c.ctxStart.Done():
					return
				case <-time.Tick(interval):
					continue
				}
			}
		}()
	}

	return nil
}

func (c *camerasByUpdateInterval) StopQueue() {
	c.cancelStart()
	c.wgStart.Wait()
	c.startedQueue.Store(false)
}

func (c *camerasByUpdateInterval) RestartQueue(ctx context.Context) error {
	c.StopQueue()

	return c.StartQueue(ctx)
}

func (c *camerasByUpdateInterval) ConsumeQueue(
	ctx context.Context,
	maxConcurrency int32,
	run func(CameraAPI),
) error {
	if !c.consumingQueue.CompareAndSwap(false, true) {
		return fmt.Errorf("queue already consumed")
	}

	ctx, cancel := context.WithCancel(ctx)
	c.ctxConsume = ctx
	c.cancelConsume = cancel

	go func() {
		count := atomic.Int32{}

		for {
			select {
			case <-c.ctxConsume.Done():
				c.wgConsume.Wait()
				return
			case camera := <-c.queue:
				for {
					if count.Load() < maxConcurrency {
						break
					}
					time.Sleep(time.Second)
				}

				count.Add(1)
				c.wgConsume.Add(1)

				go func() {
					run(camera)
					count.Add(-1)
					c.wgConsume.Done()
				}()
			}
		}
	}()

	return nil
}

func (c *camerasByUpdateInterval) StopConsume() {
	c.cancelConsume()
	c.wgConsume.Wait()
	c.consumingQueue.Store(false)
}
