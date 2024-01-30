package main

import (
	"fmt"
	"image"
	"log"
	"unsafe"

	"github.com/bluenviron/gortsplib/v4"
	"github.com/bluenviron/gortsplib/v4/pkg/description"
	"github.com/bluenviron/gortsplib/v4/pkg/format"
	"github.com/bluenviron/gortsplib/v4/pkg/format/rtph264"
	"github.com/bluenviron/gortsplib/v4/pkg/format/rtph265"
	"github.com/pion/rtp"
)

// #cgo pkg-config: libavcodec libavutil libswscale
// #include <libavcodec/avcodec.h>
// #include <libavutil/imgutils.h>
// #include <libswscale/swscale.h>
import "C"

func frameData(frame *C.AVFrame) **C.uint8_t {
	return (**C.uint8_t)(unsafe.Pointer(&frame.data[0]))
}

func frameLineSize(frame *C.AVFrame) *C.int {
	return (*C.int)(unsafe.Pointer(&frame.linesize[0]))
}

// h264Decoder is a wrapper around FFmpeg's H264 decoder.
type h264Decoder struct {
	codecCtx    *C.AVCodecContext
	srcFrame    *C.AVFrame
	swsCtx      *C.struct_SwsContext
	dstFrame    *C.AVFrame
	dstFramePtr []uint8
}

// initialize initializes a h264Decoder.
func (d *h264Decoder) initialize() error {
	codec := C.avcodec_find_decoder(C.AV_CODEC_ID_H264)
	if codec == nil {
		return fmt.Errorf("avcodec_find_decoder() failed")
	}

	d.codecCtx = C.avcodec_alloc_context3(codec)
	if d.codecCtx == nil {
		return fmt.Errorf("avcodec_alloc_context3() failed")
	}

	res := C.avcodec_open2(d.codecCtx, codec, nil)
	if res < 0 {
		C.avcodec_close(d.codecCtx)
		return fmt.Errorf("avcodec_open2() failed")
	}

	d.srcFrame = C.av_frame_alloc()
	if d.srcFrame == nil {
		C.avcodec_close(d.codecCtx)
		return fmt.Errorf("av_frame_alloc() failed")
	}

	return nil
}

// close closes the decoder.
func (d *h264Decoder) close() {
	if d.dstFrame != nil {
		C.av_frame_free(&d.dstFrame)
	}

	if d.swsCtx != nil {
		C.sws_freeContext(d.swsCtx)
	}

	C.av_frame_free(&d.srcFrame)
	C.avcodec_close(d.codecCtx)
}

func (d *h264Decoder) decode(nalu []byte) (image.Image, error) {
	nalu = append([]uint8{0x00, 0x00, 0x00, 0x01}, []uint8(nalu)...)

	// send NALU to decoder
	var avPacket C.AVPacket
	avPacket.data = (*C.uint8_t)(C.CBytes(nalu))
	defer C.free(unsafe.Pointer(avPacket.data))
	avPacket.size = C.int(len(nalu))
	res := C.avcodec_send_packet(d.codecCtx, &avPacket)
	if res < 0 {
		return nil, nil
	}

	// receive frame if available
	res = C.avcodec_receive_frame(d.codecCtx, d.srcFrame)
	if res < 0 {
		return nil, nil
	}

	// if frame size has changed, allocate needed objects
	if d.dstFrame == nil || d.dstFrame.width != d.srcFrame.width ||
		d.dstFrame.height != d.srcFrame.height {
		if d.dstFrame != nil {
			C.av_frame_free(&d.dstFrame)
		}

		if d.swsCtx != nil {
			C.sws_freeContext(d.swsCtx)
		}

		d.dstFrame = C.av_frame_alloc()
		d.dstFrame.format = C.AV_PIX_FMT_RGBA
		d.dstFrame.width = d.srcFrame.width
		d.dstFrame.height = d.srcFrame.height
		d.dstFrame.color_range = C.AVCOL_RANGE_JPEG
		res = C.av_frame_get_buffer(d.dstFrame, 1)
		if res < 0 {
			return nil, fmt.Errorf("av_frame_get_buffer() failed")
		}

		d.swsCtx = C.sws_getContext(
			d.srcFrame.width,
			d.srcFrame.height,
			C.AV_PIX_FMT_YUV420P,
			d.dstFrame.width,
			d.dstFrame.height,
			(int32)(d.dstFrame.format),
			C.SWS_BILINEAR,
			nil,
			nil,
			nil,
		)
		if d.swsCtx == nil {
			return nil, fmt.Errorf("sws_getContext() failed")
		}

		dstFrameSize := C.av_image_get_buffer_size(
			(int32)(d.dstFrame.format),
			d.dstFrame.width,
			d.dstFrame.height,
			1,
		)
		d.dstFramePtr = (*[1 << 30]uint8)(unsafe.Pointer(d.dstFrame.data[0]))[:dstFrameSize:dstFrameSize]
	}

	// convert color space from YUV420 to RGBA
	res = C.sws_scale(d.swsCtx, frameData(d.srcFrame), frameLineSize(d.srcFrame),
		0, d.srcFrame.height, frameData(d.dstFrame), frameLineSize(d.dstFrame))
	if res < 0 {
		return nil, fmt.Errorf("sws_scale() failed")
	}

	// embed frame into an image.Image
	return &image.RGBA{
		Pix:    d.dstFramePtr,
		Stride: 4 * (int)(d.dstFrame.width),
		Rect: image.Rectangle{
			Max: image.Point{(int)(d.dstFrame.width), (int)(d.dstFrame.height)},
		},
	}, nil
}

// h265Decoder is a wrapper around FFmpeg's H265 decoder.
type h265Decoder struct {
	codecCtx    *C.AVCodecContext
	srcFrame    *C.AVFrame
	swsCtx      *C.struct_SwsContext
	dstFrame    *C.AVFrame
	dstFramePtr []uint8
}

// initialize initializes a h265Decoder.
func (d *h265Decoder) initialize() error {
	codec := C.avcodec_find_decoder(C.AV_CODEC_ID_H265)
	if codec == nil {
		return fmt.Errorf("avcodec_find_decoder() failed")
	}

	d.codecCtx = C.avcodec_alloc_context3(codec)
	if d.codecCtx == nil {
		return fmt.Errorf("avcodec_alloc_context3() failed")
	}

	res := C.avcodec_open2(d.codecCtx, codec, nil)
	if res < 0 {
		C.avcodec_close(d.codecCtx)
		return fmt.Errorf("avcodec_open2() failed")
	}

	d.srcFrame = C.av_frame_alloc()
	if d.srcFrame == nil {
		C.avcodec_close(d.codecCtx)
		return fmt.Errorf("av_frame_alloc() failed")
	}

	return nil
}

// close closes the decoder.
func (d *h265Decoder) close() {
	if d.dstFrame != nil {
		C.av_frame_free(&d.dstFrame)
	}

	if d.swsCtx != nil {
		C.sws_freeContext(d.swsCtx)
	}

	C.av_frame_free(&d.srcFrame)
	C.avcodec_close(d.codecCtx)
}

func (d *h265Decoder) decode(nalu []byte) (image.Image, error) {
	nalu = append([]uint8{0x00, 0x00, 0x00, 0x01}, []uint8(nalu)...)

	// send NALU to decoder
	var avPacket C.AVPacket
	avPacket.data = (*C.uint8_t)(C.CBytes(nalu))
	defer C.free(unsafe.Pointer(avPacket.data))
	avPacket.size = C.int(len(nalu))
	res := C.avcodec_send_packet(d.codecCtx, &avPacket)
	if res < 0 {
		return nil, nil
	}

	// receive frame if available
	res = C.avcodec_receive_frame(d.codecCtx, d.srcFrame)
	if res < 0 {
		return nil, nil
	}

	// if frame size has changed, allocate needed objects
	if d.dstFrame == nil || d.dstFrame.width != d.srcFrame.width ||
		d.dstFrame.height != d.srcFrame.height {
		if d.dstFrame != nil {
			C.av_frame_free(&d.dstFrame)
		}

		if d.swsCtx != nil {
			C.sws_freeContext(d.swsCtx)
		}

		d.dstFrame = C.av_frame_alloc()
		d.dstFrame.format = C.AV_PIX_FMT_RGBA
		d.dstFrame.width = d.srcFrame.width
		d.dstFrame.height = d.srcFrame.height
		d.dstFrame.color_range = C.AVCOL_RANGE_JPEG
		res = C.av_frame_get_buffer(d.dstFrame, 1)
		if res < 0 {
			return nil, fmt.Errorf("av_frame_get_buffer() failed")
		}

		d.swsCtx = C.sws_getContext(
			d.srcFrame.width,
			d.srcFrame.height,
			C.AV_PIX_FMT_YUV420P,
			d.dstFrame.width,
			d.dstFrame.height,
			(int32)(d.dstFrame.format),
			C.SWS_BILINEAR,
			nil,
			nil,
			nil,
		)
		if d.swsCtx == nil {
			return nil, fmt.Errorf("sws_getContext() failed")
		}

		dstFrameSize := C.av_image_get_buffer_size(
			(int32)(d.dstFrame.format),
			d.dstFrame.width,
			d.dstFrame.height,
			1,
		)
		d.dstFramePtr = (*[1 << 30]uint8)(unsafe.Pointer(d.dstFrame.data[0]))[:dstFrameSize:dstFrameSize]
	}

	// convert color space from YUV420 to RGBA
	res = C.sws_scale(d.swsCtx, frameData(d.srcFrame), frameLineSize(d.srcFrame),
		0, d.srcFrame.height, frameData(d.dstFrame), frameLineSize(d.dstFrame))
	if res < 0 {
		return nil, fmt.Errorf("sws_scale() failed")
	}

	// embed frame into an image.Image
	return &image.RGBA{
		Pix:    d.dstFramePtr,
		Stride: 4 * (int)(d.dstFrame.width),
		Rect: image.Rectangle{
			Max: image.Point{(int)(d.dstFrame.width), (int)(d.dstFrame.height)},
		},
	}, nil
}

func addH264Decoder(
	client *gortsplib.Client,
	desc *description.Session,
	imgch chan<- image.Image,
) (*description.Media, error) {
	var h264 *format.H264
	media := desc.FindFormat(&h264)
	if media == nil {
		return nil, errMediaNotFound
	}

	rtpDecoder, err := h264.CreateDecoder()
	if err != nil {
		return nil, fmt.Errorf("error creating decoder: %w", err)
	}

	frameDecoder := &h264Decoder{}
	err = frameDecoder.initialize()
	if err != nil {
		return nil, fmt.Errorf("error initializing decoder: %w", err)
	}

	if h264.SPS != nil {
		frameDecoder.decode(h264.SPS)
	}
	if h264.PPS != nil {
		frameDecoder.decode(h264.PPS)
	}

	_, err = client.Setup(desc.BaseURL, media, 0, 0)
	if err != nil {
		return nil, fmt.Errorf("error setuping RTSP: %w", err)
	}

	client.OnPacketRTP(media, h264, func(pkt *rtp.Packet) {
		defer func() {
			if r := recover(); r != nil {
				fmt.Printf("Recovered in %v", r)
			}
		}()
		_, ok := client.PacketPTS(media, pkt)
		if !ok {
			return
		}

		au, err := rtpDecoder.Decode(pkt)
		if err != nil {
			if err != rtph264.ErrNonStartingPacketAndNoPrevious &&
				err != rtph264.ErrMorePacketsNeeded {
				log.Printf("error decoding packet: %s", err)
			}
			return
		}

		for _, nalu := range au {
			img, err := frameDecoder.decode(nalu)
			if err != nil {
				log.Printf("error deconding frame: %s", err)
				continue
			}

			if img == nil {
				continue
			}

			imgch <- img

			return
		}
	})

	return media, nil
}

func addH265Decoder(
	client *gortsplib.Client,
	desc *description.Session,
	imgch chan<- image.Image,
) (*description.Media, error) {
	var h265 *format.H265
	media := desc.FindFormat(&h265)
	if media == nil {
		return nil, errMediaNotFound
	}

	rtpDecoder, err := h265.CreateDecoder()
	if err != nil {
		return nil, fmt.Errorf("error creating decoder: %w", err)
	}

	frameDecoder := &h265Decoder{}
	err = frameDecoder.initialize()
	if err != nil {
		return nil, fmt.Errorf("error initializing decoder: %w", err)
	}

	if h265.VPS != nil {
		frameDecoder.decode(h265.VPS)
	}
	if h265.SPS != nil {
		frameDecoder.decode(h265.SPS)
	}
	if h265.PPS != nil {
		frameDecoder.decode(h265.PPS)
	}

	_, err = client.Setup(desc.BaseURL, media, 0, 0)
	if err != nil {
		return nil, fmt.Errorf("error setuping RTSP: %w", err)
	}

	client.OnPacketRTP(media, h265, func(pkt *rtp.Packet) {
		defer func() {
			if r := recover(); r != nil {
				fmt.Printf("Recovered in %v", r)
			}
		}()
		_, ok := client.PacketPTS(media, pkt)
		if !ok {
			return
		}

		au, err := rtpDecoder.Decode(pkt)
		if err != nil {
			if err != rtph265.ErrNonStartingPacketAndNoPrevious &&
				err != rtph265.ErrMorePacketsNeeded {
				log.Printf("error decoding packet: %s", err)
			}
			return
		}

		for _, nalu := range au {
			img, err := frameDecoder.decode(nalu)
			if err != nil {
				log.Printf("error deconding frame: %s", err)
				continue
			}

			if img == nil {
				continue
			}

			log.Println("wait channel")
			imgch <- img

			return
		}
	})

	return media, nil
}
