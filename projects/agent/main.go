package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	_ "net/http/pprof"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func makeSnapshot(cameraAPI CameraAPI) (*metrics, error) {
	metrics := newMetrics()
	defer metrics.final()

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

	contentType, body := bodyImage(camera.id, img)
	_, err = httpPost(cameraAPI.snapshotURL, camera.accessToken, contentType, body)
	if err != nil {
		return metrics, fmt.Errorf("error sending snapshot: %w", err)
	}
	metrics.add("send_snapshot")
	metrics.success = true

	return metrics, nil
}

func getCameras(agentURL string, cameraURL string, accessToken *AccessToken) ([]CameraAPI, error) {
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

	err := httpGet(url, accessToken, &data)
	if err != nil {
		return nil, fmt.Errorf("error getting cameras: %w", err)
	}

	cameras = append(cameras, data.Items...)

	for data.Page < data.Pages {
		url := fmt.Sprintf("%s?page=%d", url, data.Page+1)
		err = httpGet(url, accessToken, &data)
		if err != nil {
			return nil, fmt.Errorf("error getting cameras: %w", err)
		}

		cameras = append(cameras, data.Items...)
	}

	for index, camera := range cameras {
		cameras[index].accessToken = accessToken
		cameras[index].snapshotURL = fmt.Sprintf("%s/%s/snapshot", cameraURL, camera.ID)
	}

	return cameras, nil
}

func sendHeartbeat(heartbeatURL string, accessToken *AccessToken, healthy bool) error {
	rawdata := struct {
		Healthy bool `json:"healthy"`
	}{
		Healthy: healthy,
	}

	data, err := json.Marshal(rawdata)
	if err != nil {
		return fmt.Errorf("error creating JSON body: %w", err)
	}

	_, err = httpPost(heartbeatURL, accessToken, "application/json", bytes.NewReader(data))

	return err
}

func main() {
	log.Println("Initializing server")
	go func() {
		log.Println(http.ListenAndServe(":6060", nil))
	}()

	defer func() {
		if r := recover(); r != nil {
			log.Println(r)
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

	accessToken := NewAccessToken(config.credentials, true)
	for !accessToken.Valid() {
		time.Sleep(time.Second)
	}

	parallelSnapshots := int32(30)
	cameras := newCamerasByUpdateInterval(int(parallelSnapshots))
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

	err = cameras.ConsumeQueue(ctxCameras, parallelSnapshots, makeSnapshot)
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
