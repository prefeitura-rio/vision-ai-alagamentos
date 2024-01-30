package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"image/png"
	_ "image/png"
	"log"
	"net/url"
	"os"
	"os/signal"
	"strings"
	"sync"
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

type AccessToken struct {
	AcsessToken string `json:"access_token"`
	TokenType   string `json:"token_type"`
	ExpiresIn   int    `json:"expires_in"`
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

func getAccessToken(credentials OIDCClientCredentials) (AccessToken, error) {
	data := url.Values{
		"grant_type": {"client_credentials"},
		"client_id":  {credentials.ClientID},
		"username":   {credentials.Username},
		"password":   {credentials.Password},
		"scope":      {"profile"},
	}

	body, err := httpPost(
		credentials.TokenURL,
		AccessToken{},
		"application/x-www-form-urlencoded",
		strings.NewReader(data.Encode()),
	)
	if err != nil {
		return AccessToken{}, fmt.Errorf("error getting Access Token: %w", err)
	}

	accessToken := AccessToken{}
	err = json.Unmarshal([]byte(body), &accessToken)
	if err != nil {
		return AccessToken{}, fmt.Errorf("error parsing body: %w", err)
	}

	return accessToken, err
}

func makeSnapshot(ctx context.Context, camera *Camera, accessToken AccessToken) {
	initialTime := time.Now()

	log.Printf("Realizando a captura da camera: %s", camera.id)
	defer func() {
		delta := time.Since(initialTime).Seconds()
		log.Printf("Tempo de captura da camera %s: %.2fs", camera.id, delta)
	}()

	img, err := camera.getNextFrame(ctx)
	if err != nil {
		log.Printf("error getting frame: %s", err)
		return
	}

	buf := bytes.NewBuffer([]byte{})
	err = png.Encode(buf, img)
	if err != nil {
		log.Printf("error encoding image in png: %s", err)
		return
	}

	rawBody := struct {
		ImageBase64 string `json:"image_base64"`
	}{
		ImageBase64: base64.StdEncoding.EncodeToString(buf.Bytes()),
	}

	body, err := json.Marshal(rawBody)
	if err != nil {
		log.Printf("error encoding body: %s", err)
		return
	}

	_, err = httpPost(camera.snapshotURL, accessToken, "application/json", bytes.NewReader(body))
	if err != nil {
		log.Printf("error seding snapshot: %s", err)
		return
	}
}

func runSnapshot(ctx context.Context, camera *Camera, accessToken AccessToken) {
	log.Printf("Iniciando captura da camera: %s", camera.id)

	ticker := time.NewTicker(camera.updateInterval)
	ctxSnaphot, cancelSnapshot := context.WithTimeout(ctx, camera.updateInterval)

	err := camera.start()
	if err != nil {
		log.Printf("error starting camera stream: %s", err)
		return
	}
	defer camera.close()

	makeSnapshot(ctxSnaphot, camera, accessToken)

	for {
		select {
		case <-ctx.Done():
			log.Printf("Finalizando a captura da camera: %s", camera.id)
			cancelSnapshot()
			return

		case <-ticker.C:
			ctxSnaphot, cancelSnapshot = context.WithTimeout(ctx, camera.updateInterval)
			makeSnapshot(ctxSnaphot, camera, accessToken)
		}
	}
}

func runCameras(
	ctx context.Context,
	wg *sync.WaitGroup,
	agentURL string,
	cameraURL string,
	credentials OIDCClientCredentials,
) error {
	type apiData struct {
		Items []CameraAPI `json:"items"`
		Total int         `json:"total"`
		Page  int         `json:"page"`
		Size  int         `json:"size"`
		Pages int         `json:"pages"`
	}
	data := apiData{}

	accessToken, err := getAccessToken(credentials)
	if err != nil {
		return fmt.Errorf("error getting access token: %s\n", err)
	}

	err = httpGet(agentURL, accessToken, &data)
	if err != nil {
		return fmt.Errorf("error getting cameras: %w", err)
	}

	cameras := make([]*Camera, 0, len(data.Items))

	for _, cameraAPI := range data.Items {
		camera, err := NewCamera(cameraAPI, cameraURL)
		if err != nil {
			return fmt.Errorf("error creating new camera from API: %w", err)
		}
		cameras = append(cameras, camera)

	}

	for _, camera := range cameras {
		camera := camera
		wg.Add(1)
		go func() {
			runSnapshot(ctx, camera, accessToken)
			wg.Done()
		}()
	}

	return nil
}

func sendHeartbeat(heartbeatURL string, credentials OIDCClientCredentials, healthy bool) error {
	accessToken, err := getAccessToken(credentials)
	if err != nil {
		return fmt.Errorf("error getting access token: %s\n", err)
	}

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
	config, err := getConfig()
	if err != nil {
		log.Printf("error getting config: %s", err)
		return
	}

	osSignal := make(chan os.Signal, 1)
	log.Println("Esperando sinal de interrupção")
	signal.Notify(osSignal, syscall.SIGINT, syscall.SIGHUP, syscall.SIGTERM)

	wg := sync.WaitGroup{}
	ticker := time.NewTicker(config.heartbeat)

	for {
		ctxCameras, cancelCameras := context.WithCancel(context.Background())

		err := runCameras(ctxCameras, &wg, config.agentURL, config.cameraURL, config.credentials)
		if err != nil {
			log.Printf("Erro ao rodar as cameras: %s", err)
		}

		err = sendHeartbeat(config.heartbeatURL, config.credentials, err == nil)
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
			log.Println("Esperando as capturas serem finalizadas")
			cancelCameras()
			wg.Wait()
		}
	}
}
