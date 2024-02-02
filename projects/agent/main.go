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
	"slices"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
)

var errMediaNotFound error = fmt.Errorf("media not found")

type OIDCClientCredentials struct {
	TokenURL string
	Username string
	Password string
	ClientID string
}

type infisicalConfig struct {
	url         string
	token       string
	secretKey   string
	environment string
}

type config struct {
	agentURL     string
	cameraURL    string
	heartbeatURL string
	credentials  OIDCClientCredentials
	heartbeat    time.Duration
}

func makeSnapshot(cameraAPI CameraAPI, cameraURL string, accessToken *AccessToken) {
	initialTime := time.Now()

	log.Printf("Realizando a captura da camera: %s", cameraAPI.ID)
	defer func() {
		delta := time.Since(initialTime).Seconds()
		log.Printf("Tempo de captura da camera %s: %.2fs", cameraAPI.ID, delta)
	}()

	camera, err := NewCamera(cameraAPI, cameraURL)
	if err != nil {
		log.Printf("error creating new camera from API: %s", err)
		return
	}

	err = camera.start()
	if err != nil {
		log.Printf("error starting camera stream: %s", err)
		return
	}
	defer camera.close()

	img, err := camera.getNextFrame()
	if err != nil {
		log.Printf("error getting frame: %s", err)
		return
	}

	contentType, body := bodyImage(camera.id, img)

	_, err = httpPost(camera.snapshotURL, accessToken, contentType, body)
	if err != nil {
		log.Printf("error sending snapshot: %s", err)
		return
	}

	log.Printf("captura finalizada: %s", camera.id)
}

func runCameras(
	ctx context.Context,
	wg *sync.WaitGroup,
	agentURL string,
	cameraURL string,
	accessToken *AccessToken,
) error {
	type apiData struct {
		Items []CameraAPI `json:"items"`
		Total int         `json:"total"`
		Page  int         `json:"page"`
		Size  int         `json:"size"`
		Pages int         `json:"pages"`
	}
	data := apiData{}
	cameras := []CameraAPI{}

	err := httpGet(agentURL, accessToken, &data)
	if err != nil {
		return fmt.Errorf("error getting cameras: %w", err)
	}

	cameras = append(cameras, data.Items...)

	for data.Page != data.Pages {
		url := fmt.Sprintf("%s?page=%d", agentURL, data.Page+1)
		err = httpGet(url, accessToken, &data)
		if err != nil {
			return fmt.Errorf("error getting cameras: %w", err)
		}

		cameras = append(cameras, data.Items...)
	}

	camerasCh := make(chan CameraAPI, 30)
	camerasByUpdateInterval := map[int][]CameraAPI{}
	updateIntervals := []int{}

	for _, camera := range cameras {
		if slices.Contains(updateIntervals, camera.UpdateInterval) {
			camerasByUpdateInterval[camera.UpdateInterval] = append(
				camerasByUpdateInterval[camera.UpdateInterval],
				camera,
			)
		} else {
			camerasByUpdateInterval[camera.UpdateInterval] = []CameraAPI{camera}
			updateIntervals = append(updateIntervals, camera.UpdateInterval)
		}
	}

	go func() {
		for _, updateInterval := range updateIntervals {
			updateInterval := updateInterval
			go func() {
				interval := time.Duration(updateInterval) * time.Second
				for {
					for _, camera := range camerasByUpdateInterval[updateInterval] {
						camerasCh <- camera
					}
					select {
					case <-ctx.Done():
						return
					case <-time.Tick(interval):
						continue
					}
				}
			}()
		}
	}()

	log.Printf("Running %d cameras", len(cameras))

	count := atomic.Int32{}
	maxCount := int32(50)

	for {
		select {
		case <-ctx.Done():
			wg.Wait()
			close(camerasCh)
			return nil
		case camera := <-camerasCh:
			for {
				if count.Load() < maxCount {
					break
				}
				time.Sleep(time.Second)
			}

			count.Add(1)
			wg.Add(1)

			go func() {
				makeSnapshot(camera, cameraURL, accessToken)
				count.Add(-1)
				wg.Done()
			}()
		}
	}
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
	go func() {
		log.Println(http.ListenAndServe(":6060", nil))
	}()

	config, err := getConfig()
	if err != nil {
		log.Printf("error getting config: %s", err)
		return
	}

	accessToken := NewAccessToken(config.credentials, true)
	for !accessToken.Valid() {
		time.Sleep(time.Second)
	}
	log.Println(accessToken.GetHeader())

	osSignal := make(chan os.Signal, 1)
	signal.Notify(osSignal, syscall.SIGINT, syscall.SIGHUP, syscall.SIGTERM)
	log.Println("Esperando sinal de interrupção")

	wg := sync.WaitGroup{}
	ticker := time.NewTicker(config.heartbeat)

	ctxCameras, cancelCameras := context.WithCancel(context.Background())

	err = runCameras(ctxCameras, &wg, config.agentURL, config.cameraURL, accessToken)
	if err != nil {
		log.Printf("Erro ao rodar as cameras: %s", err)
	}

	for {
		err = sendHeartbeat(config.heartbeatURL, accessToken, err == nil)
		if err != nil {
			log.Printf("Error sending heartbeat: %s", err)
		}

		select {
		case <-osSignal:
			log.Println("Esperando as capturas serem finalizadas")
			cancelCameras()
			wg.Wait()
			log.Println("Capturas finalizadas com sucesso")

			return
		case <-ticker.C:
		}
	}
}
