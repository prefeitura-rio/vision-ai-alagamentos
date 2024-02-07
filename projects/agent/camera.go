package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"math"
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
	accessToken    *AccessToken
	rtpDecoder     rtpDecoder
	frameDecoder   *h26xDecoder
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
			ReadTimeout:       time.Duration(api.UpdateInterval) * time.Second / 2,
			OnTransportSwitch: func(err error) {},
			OnPacketLost:      func(err error) {},
		},
	}, nil
}

func (camera *Camera) setDecoders() error {
	desc, _, err := camera.client.Describe(camera.getURL)
	if err != nil {
		return fmt.Errorf("error describing camera: %w", err)
	}

	codecName := ""
	media := &description.Media{}
	initFrames := [][]byte{}

	var h265 *format.H265
	var h264 *format.H264

	if media264 := desc.FindFormat(&h264); media264 != nil {
		rtpDecoder, err := h264.CreateDecoder()
		if err != nil {
			return fmt.Errorf("error creating H264 decoder: %w", err)
		}

		codecName = "H264"
		media = media264
		initFrames = append(initFrames, h264.SPS, h264.PPS)
		camera.rtpDecoder = rtpDecoder
	} else if media265 := desc.FindFormat(&h265); media265 != nil {
		rtpDecoder, err := h265.CreateDecoder()
		if err != nil {
			return fmt.Errorf("error creating H265 decoder: %w", err)
		}

		codecName = "H265"
		media = media265
		initFrames = append(initFrames, h265.VPS, h265.SPS, h265.PPS)
		camera.rtpDecoder = rtpDecoder
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
			_, err = camera.frameDecoder.decode(frame)
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

func (camera *Camera) decodeRTPPacket(forma format.Format, pkt *rtp.Packet) ([]byte, error) {
	au, err := camera.rtpDecoder.Decode(pkt)
	if err != nil {
		return nil, err
	}

	for _, nalu := range au {
		img, err := camera.frameDecoder.decode(nalu)
		if err != nil {
			return nil, fmt.Errorf("error decoding frame: %w", err)
		}

		if img == nil {
			continue
		}

		return img, nil
	}

	return nil, errAllFrameEmpty
}

func (camera *Camera) getNextFrame() ([]byte, error) {
	imgch := make(chan []byte)
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

		img, err := camera.decodeRTPPacket(f, pkt)
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

type errSuccess[T any] struct {
	err     T
	success T
}

type camerasByUpdateInterval struct {
	ids              []string
	cameras          map[int][]CameraAPI
	intervals        []int
	queue            chan CameraAPI
	mutex            *sync.RWMutex
	startedQueue     atomic.Bool
	ctxStart         context.Context
	cancelStart      context.CancelFunc
	wgStart          *sync.WaitGroup
	consumingQueue   atomic.Bool
	ctxConsume       context.Context
	cancelConsume    context.CancelFunc
	wgConsume        *sync.WaitGroup
	processedCameras errSuccess[uint]
	timeProcessing   errSuccess[time.Duration]
	mutexMetrics     *sync.Mutex
	bucketsTimes     []time.Duration
	metrics          errSuccess[map[string]map[time.Duration]uint]
}

func newCamerasByUpdateInterval(queueBuffer int) *camerasByUpdateInterval {
	return &camerasByUpdateInterval{
		ids:              []string{},
		cameras:          map[int][]CameraAPI{},
		intervals:        []int{},
		queue:            make(chan CameraAPI, queueBuffer),
		mutex:            &sync.RWMutex{},
		startedQueue:     atomic.Bool{},
		ctxStart:         context.Background(),
		cancelStart:      func() {},
		wgStart:          &sync.WaitGroup{},
		consumingQueue:   atomic.Bool{},
		ctxConsume:       context.Background(),
		cancelConsume:    func() {},
		wgConsume:        &sync.WaitGroup{},
		processedCameras: errSuccess[uint]{0, 0},
		timeProcessing:   errSuccess[time.Duration]{0, 0},
		mutexMetrics:     &sync.Mutex{},
		metrics: errSuccess[map[string]map[time.Duration]uint]{
			err:     map[string]map[time.Duration]uint{},
			success: map[string]map[time.Duration]uint{},
		},
		bucketsTimes: []time.Duration{
			100 * time.Millisecond,
			200 * time.Millisecond,
			300 * time.Millisecond,
			400 * time.Millisecond,
			500 * time.Millisecond,
			600 * time.Millisecond,
			700 * time.Millisecond,
			800 * time.Millisecond,
			900 * time.Millisecond,
			1 * time.Second,
			2 * time.Second,
			3 * time.Second,
			4 * time.Second,
			5 * time.Second,
			6 * time.Second,
			7 * time.Second,
			8 * time.Second,
			9 * time.Second,
			10 * time.Second,
			12 * time.Second,
			14 * time.Second,
			16 * time.Second,
			18 * time.Second,
			20 * time.Second,
			22 * time.Second,
			24 * time.Second,
			26 * time.Second,
			28 * time.Second,
			30 * time.Second,
			32 * time.Second,
			35 * time.Second,
			37 * time.Second,
			40 * time.Second,
			42 * time.Second,
			45 * time.Second,
			47 * time.Second,
			50 * time.Second,
			55 * time.Second,
			60 * time.Second,
			65 * time.Second,
			70 * time.Second,
			75 * time.Second,
			80 * time.Second,
			85 * time.Second,
			90 * time.Second,
			95 * time.Second,
			100 * time.Second,
			110 * time.Second,
			120 * time.Second,
			130 * time.Second,
			140 * time.Second,
			150 * time.Second,
			160 * time.Second,
			170 * time.Second,
			180 * time.Second,
			190 * time.Second,
			200 * time.Second,
			210 * time.Second,
		},
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
				log.Printf("send %d seconds cameras to the queue", updateInterval)
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

func (c *camerasByUpdateInterval) findBucket(current time.Duration) time.Duration {
	for index, bucket := range c.bucketsTimes {
		if bucket >= current {
			return c.bucketsTimes[max(index-1, 0)]
		}
	}

	return c.bucketsTimes[len(c.bucketsTimes)-1]
}

func (c *camerasByUpdateInterval) createKey(success bool, key string) {
	if success {
		c.metrics.success[key] = map[time.Duration]uint{}
		for _, bucket := range c.bucketsTimes {
			c.metrics.success[key][bucket] = 0
		}
	} else {
		c.metrics.err[key] = map[time.Duration]uint{}
		for _, bucket := range c.bucketsTimes {
			c.metrics.err[key][bucket] = 0
		}
	}
}

func (c *camerasByUpdateInterval) proccessMetrics(allMetrics []metrics) {
	c.mutexMetrics.Lock()
	defer c.mutexMetrics.Unlock()
	for _, rawMetrics := range allMetrics {
		metrics := map[string]time.Duration{}

		for index := 1; index < len(rawMetrics.order); index++ {
			key, value := rawMetrics.diff(index)
			metrics[key] = c.findBucket(value)
		}

		key, value := rawMetrics.total()
		metrics[key] = c.findBucket(value)

		if rawMetrics.success {
			c.processedCameras.success += 1
			c.timeProcessing.success += value
			for key, value := range metrics {
				if _, ok := c.metrics.success[key]; !ok {
					c.createKey(rawMetrics.success, key)
				}
				c.metrics.success[key][value]++
			}
		} else {
			c.processedCameras.err += 1
			c.timeProcessing.err += value
			for key, value := range metrics {
				if _, ok := c.metrics.err[key]; !ok {
					c.createKey(rawMetrics.success, key)
				}
				c.metrics.err[key][value]++
			}
		}
	}

	percentile := func(key string, percentile uint) (time.Duration, time.Duration) {
		ps := (float64(percentile)/100)*(float64(c.processedCameras.success)-1) + 1
		pe := (float64(percentile)/100)*(float64(c.processedCameras.err)-1) + 1
		psi, psr := math.Modf(ps)
		pei, per := math.Modf(pe)

		psl, psh := time.Duration(0), time.Duration(0)
		pel, peh := time.Duration(0), time.Duration(0)
		st, et := uint(0), uint(0)

		for index, bucket := range c.bucketsTimes {
			if _, ok := c.metrics.success[key]; ok {
				st += c.metrics.success[key][bucket]
				if float64(st) > psi && psl == 0 {
					if float64(st)-psi > psr {
						psl, psh = bucket, bucket
					} else {
						psl, psh = bucket, c.bucketsTimes[min(index+1, len(c.bucketsTimes)-1)]
					}
				}
			}

			if _, ok := c.metrics.err[key]; ok {
				et += c.metrics.err[key][bucket]
				if float64(et) > pei && pel == 0 {
					if float64(et)-pei > per {
						pel, peh = bucket, bucket
					} else {
						pel, peh = bucket, c.bucketsTimes[min(index+1, len(c.bucketsTimes)-1)]
					}
				}
			}

			if psl != 0 && pel != 0 {
				break
			}
		}

		return psl + time.Duration(psr*float64(psh-psl)), pel + time.Duration(per*float64(peh-pel))
	}

	percentiles := func(p uint) {
		keys := make([]string, 0, max(len(c.metrics.err), len(c.metrics.success)))
		for key := range c.metrics.success {
			keys = append(keys, key)
		}
		for key := range c.metrics.err {
			if !slices.Contains(keys, key) {
				keys = append(keys, key)
			}
		}

		slices.Sort(keys)

		for _, key := range keys {
			psuccess, perr := percentile(key, p)
			log.Printf("%s P%d success: %s err: %s", key, p, psuccess, perr)
		}
	}

	percentiles(uint(10))
	percentiles(uint(25))
	percentiles(uint(50))
	percentiles(uint(75))
	percentiles(uint(95))
	percentiles(uint(99))
	log.Println("processed cameras success:", c.processedCameras.success)
	log.Printf("time processing success: %.2f", c.timeProcessing.success.Seconds())
	log.Printf(
		"time processing avg success: %.2f",
		c.timeProcessing.success.Seconds()/float64(c.processedCameras.success),
	)
	log.Println("processed cameras err:", c.processedCameras.err)
	log.Printf("time processing err: %.2f", c.timeProcessing.err.Seconds())
	log.Printf(
		"time processing avg err: %.2f",
		c.timeProcessing.err.Seconds()/float64(c.processedCameras.err),
	)
}

func (c *camerasByUpdateInterval) ConsumeQueue(
	ctx context.Context,
	maxConcurrency int32,
	run func(CameraAPI) (*metrics, error),
) error {
	if !c.consumingQueue.CompareAndSwap(false, true) {
		return fmt.Errorf("queue already consumed")
	}

	ctx, cancel := context.WithCancel(ctx)
	c.ctxConsume = ctx
	c.cancelConsume = cancel
	// metricsCh := make(chan metrics, maxConcurrency*100)

	// go func() {
	// 	allMetrics := make([]metrics, 0, maxConcurrency*100)
	// 	ticker := time.NewTicker(time.Second * 10)
	// 	defer ticker.Stop()
	// 	for {
	// 		select {
	// 		case <-ticker.C:
	// 			buffer := make([]metrics, len(allMetrics))
	// 			copy(buffer, allMetrics)
	// 			go c.proccessMetrics(buffer)
	// 			clear(allMetrics)
	// 		case metrics, more := <-metricsCh:
	// 			if !more {
	// 				c.proccessMetrics(allMetrics)
	// 				return
	// 			}
	// 			allMetrics = append(allMetrics, metrics)
	// 		}
	// 	}
	// }()

	go func() {
		count := atomic.Int32{}

		for {
			select {
			case <-c.ctxConsume.Done():
				c.wgConsume.Wait()
				// close(metricsCh)
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
					_, err := run(camera)
					if err != nil {
						log.Printf("error running: %s", err)
					}
					count.Add(-1)
					// metricsCh <- metrics{
					// 	data:    m.data,
					// 	order:   m.order,
					// 	success: m.success,
					// }
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
