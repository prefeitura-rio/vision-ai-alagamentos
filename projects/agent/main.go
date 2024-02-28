package main

import (
	"bytes"
	"context"
	"crypto/md5"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	_ "net/http/pprof"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/prefeitura-rio/vision-ai/libs"
)

func makeSnapshot(cameraAPI CameraAPI) (*metrics, error) {
	metrics := newMetrics()
	defer metrics.stop(false)

	camera, err := NewCamera(cameraAPI)
	if err != nil {
		return metrics, fmt.Errorf("error creating new camera from API: %w", err)
	}

	metrics.add("setup")

	err = camera.start()
	if err != nil {
		return metrics, fmt.Errorf("error starting camera stream: %w", err)
	}

	defer camera.close()
	metrics.add("start")

	img, err := camera.getNextFrame()
	if err != nil {
		return metrics, fmt.Errorf("error getting frame: %w", err)
	}

	metrics.add("get_next_frame")

	sum := md5.Sum(img)
	hash := base64.StdEncoding.EncodeToString(sum[:])
	contentLength := len(img)
	bodyData := struct {
		HashMD5       string `json:"hash_md5"`
		ContentLength int    `json:"content_length"`
	}{
		HashMD5:       hash,
		ContentLength: contentLength,
	}

	bodyRequest, err := json.Marshal(bodyData)
	if err != nil {
		return metrics, fmt.Errorf("error creating snapshot body: %w", err)
	}

	metrics.add("create_snapshot_body")

	bodyResponse, err := libs.HTTPPost(
		cameraAPI.snapshotURL,
		camera.accessToken,
		"application/json",
		bytes.NewReader(bodyRequest),
	)
	if err != nil {
		return metrics, fmt.Errorf("error creating snapshot: %w", err)
	}

	metrics.add("create_snapshot")

	snapshot := struct {
		ID       string `json:"id"`
		CameraID string `json:"camera_id"`
		ImageURL string `json:"image_url"`
	}{}

	err = json.Unmarshal(bodyResponse, &snapshot)
	if err != nil {
		return metrics, fmt.Errorf("error parsing body: %w", err)
	}

	metrics.add("unmarshal_snapshot")

	headers := map[string]string{
		"Content-Type": "image/png",
		"Content-MD5":  hash,
	}

	_, err = libs.HTTPPut(
		snapshot.ImageURL,
		headers,
		bytes.NewReader(img),
	)
	if err != nil {
		return metrics, fmt.Errorf("error sending snapshot: %w", err)
	}

	metrics.add("send_snapshot")

	preditcURL := cameraAPI.snapshotURL + "/" + snapshot.ID + "/predict"

	_, err = libs.HTTPPost(preditcURL, camera.accessToken, "application/json", nil)
	if err != nil {
		return metrics, fmt.Errorf("error creating predictions: %w", err)
	}

	metrics.add("create_predictions")

	metrics.stop(true)

	return metrics, nil
}

func getCameras(agentURL string, cameraURL string, accessToken *libs.AccessToken) ([]CameraAPI, error) {
	type apiData struct {
		Items []CameraAPI `json:"items"`
		Total int         `json:"total"`
		Page  int         `json:"page"`
		Size  int         `json:"size"`
		Pages int         `json:"pages"`
	}

	data := apiData{}
	cameras := []CameraAPI{}
	url := agentURL + "/cameras"

	err := libs.HTTPGet(url, accessToken, &data)
	if err != nil {
		return nil, fmt.Errorf("error getting cameras: %w", err)
	}

	cameras = append(cameras, data.Items...)

	for data.Page < data.Pages {
		url := fmt.Sprintf("%s?page=%d", url, data.Page+1)

		err = libs.HTTPGet(url, accessToken, &data)
		if err != nil {
			return nil, fmt.Errorf("error getting cameras: %w", err)
		}

		cameras = append(cameras, data.Items...)
	}

	for index, camera := range cameras {
		cameras[index].accessToken = accessToken
		cameras[index].snapshotURL = fmt.Sprintf("%s/%s/snapshots", cameraURL, camera.ID)
	}

	return cameras, nil
}

func sendHeartbeat(heartbeatURL string, accessToken *libs.AccessToken, healthy bool) error {
	rawdata := map[string]bool{"healthy": healthy}

	data, err := json.Marshal(rawdata)
	if err != nil {
		return fmt.Errorf("error creating JSON body: %w", err)
	}

	_, err = libs.HTTPPost(heartbeatURL, accessToken, "application/json", bytes.NewReader(data))

	return fmt.Errorf("error send heartbeat: %w", err)
}

func main() {
	log.Println("Initializing server")

	go func() {
		log.Println(http.ListenAndServe(":6060", nil))
	}()

	defer func() {
		if r := recover(); r != nil {
			log.Println(r)
			os.Exit(1)
		}
	}()

	config, err := getConfig()
	if err != nil {
		panic(fmt.Errorf("error getting config: %w", err))
	}

	urls := struct{ camera, agent string }{
		camera: fmt.Sprintf("%s/cameras", config.apiBaseURL),
		agent:  fmt.Sprintf("%s/agents/%s", config.apiBaseURL, config.agentID),
	}

	accessToken := libs.NewAccessToken(config.credentials, true)
	for !accessToken.Valid() {
		time.Sleep(time.Second)
	}

	cameras := newCameraPool(config.parallelSnapshots)
	ctxCameras, cancelCameras := context.WithCancel(context.Background())

	defer func() {
		log.Println("Esperando as capturas serem finalizadas")
		cancelCameras()
		cameras.StopQueue()
		cameras.StopConsume()
		log.Println("Capturas finalizadas com sucesso")
	}()

	err = cameras.StartQueue(ctxCameras)
	if err != nil {
		panic(fmt.Errorf("error starting queue: %w", err))
	}

	err = cameras.ConsumeQueue(ctxCameras, config.parallelSnapshots, makeSnapshot)
	if err != nil {
		panic(fmt.Errorf("error consuming queue: %w", err))
	}

	ticker := time.NewTicker(config.heartbeat)
	defer ticker.Stop()

	osSignal := make(chan os.Signal, 1)
	signal.Notify(osSignal, syscall.SIGINT, syscall.SIGHUP, syscall.SIGTERM)
	log.Println("waiting stop signal from OS")

	log.Printf("server intialized successfully")

	for {
		camerasAPI, err := getCameras(urls.agent, urls.camera, accessToken)
		if err != nil {
			log.Printf("error getting cameras: %s", err)
		} else if !cameras.Equals(camerasAPI) {
			log.Printf("replacing cameras")

			cameras.Replace(camerasAPI)

			err = cameras.RestartQueue(ctxCameras)
			if err != nil {
				log.Printf("error restating queue: %s", err)
			}

			log.Printf("running %d cameras", cameras.Len())
		}

		err = sendHeartbeat(urls.agent+"/heartbeat", accessToken, err == nil)
		if err != nil {
			log.Printf("error sending heartbeat: %s", err)
		}

		select {
		case <-osSignal:
			return
		case <-ticker.C:
			continue
		}
	}
}
