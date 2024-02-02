package main

import (
	"fmt"
	"image"
	"unsafe"

	"github.com/pion/rtp"
)

// #cgo pkg-config: libavcodec libavutil libswscale
// #include <libavcodec/avcodec.h>
// #include <libavutil/imgutils.h>
// #include <libswscale/swscale.h>
import "C"

var errAllFrameEmpty error = fmt.Errorf("all frames is empty")

type rtpDecoder interface {
	Decode(*rtp.Packet) ([][]byte, error)
}

func frameData(frame *C.AVFrame) **C.uint8_t {
	return (**C.uint8_t)(unsafe.Pointer(&frame.data[0]))
}

func frameLineSize(frame *C.AVFrame) *C.int {
	return (*C.int)(unsafe.Pointer(&frame.linesize[0]))
}

// h26xDecoder is a wrapper around FFmpeg's H264/H265 decoder.
type h26xDecoder struct {
	videoCodecCtx *C.AVCodecContext
	naluFrame     *C.AVFrame
	videoSwsCtx   *C.struct_SwsContext
	avFrame       *C.AVFrame
	avFrameData   []uint8
}

// initialize initializes a h26xDecoder.
func (d *h26xDecoder) initialize(codecName string) error {
	codecCode := uint32(C.AV_CODEC_ID_NONE)
	if codecName == "H264" {
		codecCode = uint32(C.AV_CODEC_ID_H264)
	} else if codecName == "H265" {
		codecCode = uint32(C.AV_CODEC_ID_H265)
	} else {
		return fmt.Errorf("codec not found")
	}

	codec := C.avcodec_find_decoder(codecCode)
	if codec == nil {
		return fmt.Errorf("avcodec_find_decoder() failed")
	}

	d.videoCodecCtx = C.avcodec_alloc_context3(codec)
	if d.videoCodecCtx == nil {
		return fmt.Errorf("avcodec_alloc_context3() failed")
	}

	res := C.avcodec_open2(d.videoCodecCtx, codec, nil)
	if res < 0 {
		C.avcodec_close(d.videoCodecCtx)
		return fmt.Errorf("avcodec_open2() failed")
	}

	d.naluFrame = C.av_frame_alloc()
	if d.naluFrame == nil {
		C.avcodec_close(d.videoCodecCtx)
		return fmt.Errorf("av_frame_alloc() failed")
	}

	return nil
}

// close closes the decoder.
func (d *h26xDecoder) close() {
	if d.avFrame != nil {
		C.av_frame_free(&d.avFrame)
	}

	if d.videoSwsCtx != nil {
		C.sws_freeContext(d.videoSwsCtx)
	}

	C.av_frame_free(&d.naluFrame)
	C.avcodec_close(d.videoCodecCtx)
}

func (d *h26xDecoder) decode(nalu []byte) (image.Image, error) {
	nalu = append([]uint8{0x00, 0x00, 0x00, 0x01}, []uint8(nalu)...)

	// send NALU to decoder
	var avPacket C.AVPacket
	avPacket.data = (*C.uint8_t)(C.CBytes(nalu))
	defer C.free(unsafe.Pointer(avPacket.data))
	avPacket.size = C.int(len(nalu))
	res := C.avcodec_send_packet(d.videoCodecCtx, &avPacket)
	if res < 0 {
		return nil, nil
	}

	// receive frame if available
	res = C.avcodec_receive_frame(d.videoCodecCtx, d.naluFrame)
	if res < 0 {
		return nil, nil
	}

	// if frame size has changed, allocate needed objects
	if d.avFrame == nil || d.avFrame.width != d.naluFrame.width ||
		d.avFrame.height != d.naluFrame.height {
		if d.avFrame != nil {
			C.av_frame_free(&d.avFrame)
		}

		if d.videoSwsCtx != nil {
			C.sws_freeContext(d.videoSwsCtx)
		}

		d.avFrame = C.av_frame_alloc()
		d.avFrame.format = C.AV_PIX_FMT_RGBA
		d.avFrame.width = d.naluFrame.width
		d.avFrame.height = d.naluFrame.height
		d.avFrame.color_range = C.AVCOL_RANGE_JPEG
		res = C.av_frame_get_buffer(d.avFrame, 1)
		if res < 0 {
			return nil, fmt.Errorf("av_frame_get_buffer() failed")
		}

		d.videoSwsCtx = C.sws_getContext(
			d.naluFrame.width,
			d.naluFrame.height,
			C.AV_PIX_FMT_YUV420P,
			d.avFrame.width,
			d.avFrame.height,
			(int32)(d.avFrame.format),
			C.SWS_BILINEAR,
			nil,
			nil,
			nil,
		)
		if d.videoSwsCtx == nil {
			return nil, fmt.Errorf("sws_getContext() failed")
		}

		dstFrameSize := C.av_image_get_buffer_size(
			(int32)(d.avFrame.format),
			d.avFrame.width,
			d.avFrame.height,
			1,
		)
		d.avFrameData = (*[1 << 30]uint8)(unsafe.Pointer(d.avFrame.data[0]))[:dstFrameSize:dstFrameSize]
	}

	// convert color space from YUV420 to RGBA
	res = C.sws_scale(d.videoSwsCtx, frameData(d.naluFrame), frameLineSize(d.naluFrame),
		0, d.naluFrame.height, frameData(d.avFrame), frameLineSize(d.avFrame))
	if res < 0 {
		return nil, fmt.Errorf("sws_scale() failed")
	}

	// embed frame into an image.Image
	return &image.RGBA{
		Pix:    d.avFrameData,
		Stride: 4 * (int)(d.avFrame.width),
		Rect: image.Rectangle{
			Max: image.Point{(int)(d.avFrame.width), (int)(d.avFrame.height)},
		},
	}, nil
}
