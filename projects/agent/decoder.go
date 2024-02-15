//nolint:nlreturn, gocritic
package main

// #cgo pkg-config: libavcodec libavutil libswscale
// #include <libavcodec/avcodec.h>
// #include <libavutil/imgutils.h>
// #include <libavutil/log.h>
// #include <libswscale/swscale.h>
import "C"

import (
	"fmt"
	"unsafe"

	"github.com/pion/rtp"
)

var (
	errAllFrameEmpty         = fmt.Errorf("all frames is empty")
	errCodecNotFound         = fmt.Errorf("codec not found")
	errAvcodecFindEncoder    = fmt.Errorf("avcodec_find_encoder failed")
	errAvcodecFindDecoder    = fmt.Errorf("avcodec_find_decoder failed")
	errAvcodecAllocContext   = fmt.Errorf("avcodec_alloc_context3 failed")
	errAvcodecOpen           = fmt.Errorf("avcodec_open2 failed")
	errAvcodecSendFrame      = fmt.Errorf("avcodec_send_frame failed")
	errAvcodecReceivePacket  = fmt.Errorf("avcodec_receive_packet failed")
	errAvcodecPacketAlloc    = fmt.Errorf("avcodec_packet_alloc failed")
	errAvcodecFrameAlloc     = fmt.Errorf("avcodec_frame_alloc failed")
	errAvcodecFrameGetBuffer = fmt.Errorf("av_frame_get_buffer failed")
	errSwcContext            = fmt.Errorf("sws_getContext failed")
	errSwsScale              = fmt.Errorf("sws_scale failed")
)

func init() { //nolint:gochecknoinits
	C.av_log_set_level(C.AV_LOG_FATAL)
}

type rtpDecoder interface {
	Decode(*rtp.Packet) ([][]byte, error)
}

func frameData(frame *C.AVFrame) **C.uint8_t {
	return (**C.uint8_t)(unsafe.Pointer(&frame.data[0]))
}

func frameLineSize(frame *C.AVFrame) *C.int {
	return (*C.int)(unsafe.Pointer(&frame.linesize[0]))
}

func pngEncoder(frame *C.AVFrame) (*C.AVPacket, error) {
	imageCodec := C.avcodec_find_encoder(C.AV_CODEC_ID_PNG)
	if imageCodec == nil {
		return nil, errAvcodecFindEncoder
	}

	codecCtx := C.avcodec_alloc_context3(imageCodec)
	if codecCtx == nil {
		return nil, errAvcodecAllocContext
	}
	defer C.avcodec_close(codecCtx)

	codecCtx.time_base = C.AVRational{1, 25}
	codecCtx.width = frame.width
	codecCtx.height = frame.height
	codecCtx.pix_fmt = C.AV_PIX_FMT_RGBA

	res := C.avcodec_open2(codecCtx, imageCodec, nil)
	if res < 0 {
		return nil, errAvcodecOpen
	}

	packet := C.av_packet_alloc()
	if packet == nil {
		return nil, errAvcodecPacketAlloc
	}

	res = C.avcodec_send_frame(codecCtx, frame)
	if res < 0 {
		C.av_packet_free(&packet)
		return nil, errAvcodecSendFrame
	}

	res = C.avcodec_receive_packet(codecCtx, packet)
	if res < 0 {
		C.av_packet_free(&packet)
		return nil, errAvcodecReceivePacket
	}

	return packet, nil
}

// h26xDecoder is a wrapper around FFmpeg's H264/H265 decoder.
type h26xDecoder struct {
	codecCtx    *C.AVCodecContext
	imagePacket *C.AVPacket
}

// initialize initializes a h26xDecoder.
func (d *h26xDecoder) initialize(codecName string) error {
	var codecCode uint32
	switch codecName {
	case "H264":
		codecCode = uint32(C.AV_CODEC_ID_H264)
	case "H265":
		codecCode = uint32(C.AV_CODEC_ID_H265)
	default:
		return errCodecNotFound
	}

	codec := C.avcodec_find_decoder(codecCode)
	if codec == nil {
		return errAvcodecFindDecoder
	}

	d.codecCtx = C.avcodec_alloc_context3(codec)
	if d.codecCtx == nil {
		return errAvcodecAllocContext
	}

	res := C.avcodec_open2(d.codecCtx, codec, nil)
	if res < 0 {
		C.avcodec_close(d.codecCtx)
		return errAvcodecOpen
	}

	return nil
}

func (d *h26xDecoder) imageIsEmpty() bool {
	return d.imagePacket == nil
}

func (d *h26xDecoder) image() []byte {
	if d.imageIsEmpty() {
		return []byte{}
	}

	return (*[1 << 30]uint8)(unsafe.Pointer(d.imagePacket.data))[:d.imagePacket.size:d.imagePacket.size]
}

// close closes the decoder.
func (d *h26xDecoder) close() {
	if !d.imageIsEmpty() {
		C.av_packet_free(&d.imagePacket)
	}

	C.avcodec_close(d.codecCtx)
}

func (d *h26xDecoder) decode(nalu []byte) error {
	nalu = append([]byte{0x00, 0x00, 0x00, 0x01}, nalu...)

	packet := C.AVPacket{
		data: (*C.uint8_t)(C.CBytes(nalu)),
		size: C.int(len(nalu)),
	}
	defer C.free(unsafe.Pointer(packet.data))

	res := C.avcodec_send_packet(d.codecCtx, &packet)
	if res < 0 {
		return nil
	}

	rawFrame := C.av_frame_alloc()
	if rawFrame == nil {
		return errAvcodecFrameAlloc
	}
	defer C.av_frame_free(&rawFrame)

	res = C.avcodec_receive_frame(d.codecCtx, rawFrame)
	if res < 0 {
		return nil
	}

	rgbaFrame := C.av_frame_alloc()
	if rgbaFrame == nil {
		return errAvcodecFrameAlloc
	}
	defer C.av_frame_free(&rgbaFrame)

	rgbaFrame.format = C.AV_PIX_FMT_RGBA
	rgbaFrame.width = rawFrame.width
	rgbaFrame.height = rawFrame.height
	rgbaFrame.color_range = C.AVCOL_RANGE_JPEG

	res = C.av_frame_get_buffer(rgbaFrame, 1)
	if res < 0 {
		return errAvcodecFrameGetBuffer
	}

	swsCtx := C.sws_getContext(
		rawFrame.width,
		rawFrame.height,
		C.AV_PIX_FMT_YUV420P,
		rgbaFrame.width,
		rgbaFrame.height,
		C.AV_PIX_FMT_RGBA,
		C.SWS_BILINEAR,
		nil,
		nil,
		nil,
	)
	if swsCtx == nil {
		return errSwcContext
	}
	defer C.sws_freeContext(swsCtx)

	res = C.sws_scale(
		swsCtx,
		frameData(rawFrame),
		frameLineSize(rawFrame),
		0,
		rawFrame.height,
		frameData(rgbaFrame),
		frameLineSize(rgbaFrame),
	)
	if res < 0 {
		return errSwsScale
	}

	imagePacket, err := pngEncoder(rgbaFrame)
	if err != nil {
		return err
	}

	d.imagePacket = imagePacket

	return nil
}
