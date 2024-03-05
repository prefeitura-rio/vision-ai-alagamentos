package main

import (
	"context"
	"errors"
	"fmt"
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
	"github.com/prefeitura-rio/vision-ai/libs"
)

var (
	ErrGetFrameTimeout   = fmt.Errorf("timeout on getting frame")
	ErrMediaNotFound     = fmt.Errorf("media not found")
	errQueueConsume      = fmt.Errorf("queue already consumed")
	errQueueStart        = fmt.Errorf("queue already started")
	errUpdateIntervalGT0 = fmt.Errorf("update interval must be greater than zero")
)

type CameraAPI struct {
	ID             string `json:"id"`
	RtspURL        string `json:"rtsp_url"`
	UpdateInterval int    `json:"update_interval"`
	snapshotURL    string
	accessToken    *libs.AccessToken
}

type Camera struct {
	id             string
	getURL         *base.URL
	updateInterval time.Duration
	client         *gortsplib.Client
	accessToken    *libs.AccessToken
	rtpDecoder     rtpDecoder
	frameDecoder   *h26xDecoder
}

func NewCamera(api CameraAPI) (*Camera, error) {
	url, err := base.ParseURL(api.RtspURL)
	if err != nil {
		return nil, fmt.Errorf("error parsing RTSP URL: %w", err)
	}

	if api.UpdateInterval <= 0 {
		return nil, errUpdateIntervalGT0
	}

	updateInterval := time.Duration(api.UpdateInterval) * time.Second

	return &Camera{
		id:             api.ID,
		getURL:         url,
		updateInterval: updateInterval,
		accessToken:    api.accessToken,
		client: &gortsplib.Client{
			ReadTimeout:       updateInterval / 2, //nolint:gomnd
			OnTransportSwitch: func(_ error) {},
			OnPacketLost:      func(_ error) {},
		},
	}, nil
}

func (camera *Camera) setDecoders() error {
	desc, _, err := camera.client.Describe(camera.getURL)
	if err != nil {
		return fmt.Errorf("error describing camera: %w", err)
	}

	var (
		codecName string
		media     *description.Media
	)

	initFrames := [][]byte{}

	var (
		h265 *format.H265
		h264 *format.H264
	)

	if media264 := desc.FindFormat(&h264); media264 != nil {
		rtpDecoder, err := h264.CreateDecoder()
		if err != nil {
			return fmt.Errorf("error creating H264 decoder: %w", err)
		}

		codecName = "H264"
		media = media264
		camera.rtpDecoder = rtpDecoder

		initFrames = append(initFrames, h264.SPS, h264.PPS)
	} else if media265 := desc.FindFormat(&h265); media265 != nil {
		rtpDecoder, err := h265.CreateDecoder()
		if err != nil {
			return fmt.Errorf("error creating H265 decoder: %w", err)
		}

		codecName = "H265"
		media = media265
		camera.rtpDecoder = rtpDecoder

		initFrames = append(initFrames, h265.VPS, h265.SPS, h265.PPS)
	} else {
		return ErrMediaNotFound
	}

	camera.frameDecoder = &h26xDecoder{}

	err = camera.frameDecoder.initialize(codecName)
	if err != nil {
		return fmt.Errorf("error initializing H265 decoder: %w", err)
	}

	for _, frame := range initFrames {
		if frame != nil {
			err = camera.frameDecoder.decode(frame)
			if err != nil {
				return fmt.Errorf("error adding initial frames: %w", err)
			}
		}
	}

	_, err = camera.client.Setup(desc.BaseURL, media, 0, 0)
	if err != nil {
		return fmt.Errorf("error setuping medias: %w", err)
	}

	return nil
}

func (camera *Camera) closeDecoders() {
	camera.frameDecoder.close()
}

func (camera *Camera) decodeRTPPacket(_ format.Format, pkt *rtp.Packet) error {
	au, err := camera.rtpDecoder.Decode(pkt)
	if err != nil {
		return fmt.Errorf("error decoding rtp: %w", err)
	}

	for _, nalu := range au {
		err := camera.frameDecoder.decode(nalu)
		if err != nil {
			return fmt.Errorf("error decoding frame: %w", err)
		}

		if camera.frameDecoder.imageIsEmpty() {
			continue
		}

		return nil
	}

	return errAllFrameEmpty
}

func (camera *Camera) getNextFrame() ([]byte, error) {
	finish := make(chan bool)
	decoded := false
	mutex := sync.Mutex{}

	defer close(finish)

	camera.client.OnPacketRTPAny(
		func(media *description.Media, forma format.Format, pkt *rtp.Packet) {
			defer func() {
				if r := recover(); r != nil {
					log.Printf("error getting next frame: %s", r)
				}
			}()

			_, ok := camera.client.PacketPTS(media, pkt)
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

			mutex.Lock()
			defer mutex.Unlock()

			if decoded {
				return
			}

			err := camera.decodeRTPPacket(forma, pkt)
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
				decoded = true
				finish <- true
			}
		},
	)
	defer camera.client.OnPacketRTPAny(
		func(_ *description.Media, _ format.Format, _ *rtp.Packet) {},
	)

	_, err := camera.client.Play(nil)
	if err != nil {
		return nil, fmt.Errorf("error playing stream: %w", err)
	}

	defer func() {
		_, err := camera.client.Pause()
		if err != nil {
			log.Printf("error pausing client: %s", err)
		}
	}()

	tick := time.NewTicker(camera.updateInterval / 2) //nolint:gomnd
	defer tick.Stop()

	select {
	case <-tick.C:
		return nil, ErrGetFrameTimeout
	case <-finish:
		return camera.frameDecoder.image(), nil
	}
}

func (camera *Camera) start() error {
	err := camera.client.Start(camera.getURL.Scheme, camera.getURL.Host)
	if err != nil {
		return fmt.Errorf("error connecting to the server: %w", err)
	}

	err = camera.setDecoders()
	if err != nil {
		camera.client.Close()

		return fmt.Errorf("error set decoders: %w", err)
	}

	return nil
}

func (camera *Camera) close() {
	camera.closeDecoders()
	camera.client.Close()
}

//nolint:containedctx
type cameraPool struct {
	ids                []string
	cameras            map[int][]CameraAPI
	intervals          []int
	queue              chan CameraAPI
	mutex              *sync.RWMutex
	startedQueue       atomic.Bool
	ctxStart           context.Context
	cancelStart        context.CancelFunc
	wgStart            *sync.WaitGroup
	consumingQueue     atomic.Bool
	ctxConsume         context.Context
	cancelConsume      context.CancelFunc
	wgConsume          *sync.WaitGroup
	metricsAggregation *metricsAggregation
}

func newCameraPool(queueBuffer int) *cameraPool {
	ctxStart, cancelStart := context.WithCancel(context.Background())
	ctxConsume, cancelConsume := context.WithCancel(context.Background())

	return &cameraPool{
		ids:                []string{},
		cameras:            map[int][]CameraAPI{},
		intervals:          []int{},
		queue:              make(chan CameraAPI, queueBuffer),
		mutex:              &sync.RWMutex{},
		startedQueue:       atomic.Bool{},
		ctxStart:           ctxStart,
		cancelStart:        cancelStart,
		wgStart:            &sync.WaitGroup{},
		consumingQueue:     atomic.Bool{},
		ctxConsume:         ctxConsume,
		cancelConsume:      cancelConsume,
		wgConsume:          &sync.WaitGroup{},
		metricsAggregation: newMetricsAggregation(),
	}
}

func (c *cameraPool) Replace(cameras []CameraAPI) {
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

func (c *cameraPool) Equals(camerasAPI []CameraAPI) bool {
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

func (c *cameraPool) Len() int {
	c.mutex.RLock()
	defer c.mutex.RUnlock()

	return len(c.ids)
}

func (c *cameraPool) StartQueue(ctx context.Context) error {
	if !c.startedQueue.CompareAndSwap(false, true) {
		return errQueueStart
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
			ticker := time.NewTicker(interval)

			defer ticker.Stop()

			for {
				log.Printf("send %d seconds cameras to the queue", updateInterval)
				cameras := make([]CameraAPI, len(c.cameras[updateInterval]))

				c.mutex.RLock()
				copy(cameras, c.cameras[updateInterval])
				c.mutex.RUnlock()

				for _, camera := range cameras {
					c.queue <- camera
				}

				select {
				case <-c.ctxStart.Done():
					return
				case <-ticker.C:
					continue
				}
			}
		}()
	}

	return nil
}

func (c *cameraPool) StopQueue() {
	c.cancelStart()
	c.wgStart.Wait()
	c.startedQueue.Store(false)
}

func (c *cameraPool) RestartQueue(ctx context.Context) error {
	c.StopQueue()

	return c.StartQueue(ctx)
}

func (c *cameraPool) registerMetrics(metricsCh <-chan *metrics, bufferSize int) {
	allMetrics := make([]*metrics, 0, bufferSize)
	ticker := time.NewTicker(time.Minute)

	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			buffer := make([]*metrics, len(allMetrics))
			copy(buffer, allMetrics)
			clear(allMetrics)
			allMetrics = allMetrics[:0]

			go func() {
				c.metricsAggregation.addMetrics(buffer)
				c.metricsAggregation.printPercentiles()
			}()
		case metrics, more := <-metricsCh:
			if !more {
				c.metricsAggregation.addMetrics(allMetrics)
				c.metricsAggregation.printPercentiles()

				return
			}

			allMetrics = append(allMetrics, metrics)
		}
	}
}

func (c *cameraPool) ConsumeQueue(
	ctx context.Context,
	maxWorkers int,
	run func(CameraAPI) (*metrics, error),
) error {
	if !c.consumingQueue.CompareAndSwap(false, true) {
		return errQueueConsume
	}

	ctx, cancel := context.WithCancel(ctx)
	c.ctxConsume = ctx
	c.cancelConsume = cancel
	bufferSize := 200
	metricsCh := make(chan *metrics, maxWorkers*bufferSize)
	workerCh := make(chan CameraAPI)
	count := atomic.Int64{}

	c.wgConsume.Add(maxWorkers)

	for range maxWorkers {
		go func() {
			defer c.wgConsume.Done()

			for camera := range workerCh {
				count.Add(1)

				metrics, err := run(camera)
				if err != nil {
					log.Printf("error running camera with ID '%s': %s", camera.ID, err)
				}

				metricsCh <- metrics

				count.Add(-1)
			}
		}()
	}

	go c.registerMetrics(metricsCh, maxWorkers*bufferSize)

	go func() {
		for {
			select {
			case <-c.ctxConsume.Done():
				close(workerCh)
				c.wgConsume.Wait()
				close(metricsCh)

				return
			case camera := <-c.queue:
				workerCh <- camera
			}
		}
	}()

	return nil
}

func (c *cameraPool) StopConsume() {
	c.cancelConsume()
	c.wgConsume.Wait()
	c.consumingQueue.Store(false)
}
