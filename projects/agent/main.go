package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/url"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"gocv.io/x/gocv"
)

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

type Camera struct {
	ID             string `json:"id"`
	RTSP_URL       string `json:"rtsp_url"`
	UpdateInterval int    `json:"update_interval"`
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
	}

	body, err := httpPost(
		credentials.TokenURL,
		AccessToken{},
		"application/x-www-form-urlencoded",
		strings.NewReader(data.Encode()),
	)
	if err != nil {
		return AccessToken{}, fmt.Errorf("Error getting Access Token: %w", err)
	}

	accessToken := AccessToken{}
	err = json.Unmarshal([]byte(body), &accessToken)
	if err != nil {
		return AccessToken{}, fmt.Errorf("Error parsing body: %w", err)
	}

	return accessToken, err
}

func getCameraSnapshot(url string) (string, error) {
	webcam, err := gocv.OpenVideoCapture(url)
	if err != nil {
		return "", fmt.Errorf("Error opening video capture device: %w", err)
	}
	defer webcam.Close()

	img := gocv.NewMat()
	defer img.Close()

	ok := webcam.Read(&img)
	if !ok {
		return "", fmt.Errorf("cannot read device %s", url)
	}

	if img.Empty() {
		return "", fmt.Errorf("no image on device %s", url)
	}

	return base64.StdEncoding.EncodeToString(img.ToBytes()), nil
}

func sendSnapashot(cameraURL string, accessToken AccessToken, image string) error {
	rawdata := struct {
		ImageBase64 string `json:"image_base64"`
	}{
		ImageBase64: image,
	}

	data, err := json.Marshal(rawdata)
	if err != nil {
		return fmt.Errorf("Error creating JSON body: %w", err)
	}

	_, err = httpPost(cameraURL, accessToken, "application/json", bytes.NewReader(data))

	return err
}

func processSnapshot(rtspURL string, snapshotURL string, accessToken AccessToken) error {
	imageb64, err := getCameraSnapshot(rtspURL)
	if err != nil {
		return fmt.Errorf("Erro ao pegar captura: %s", err)
	}

	err = sendSnapashot(snapshotURL, accessToken, imageb64)
	if err != nil {
		return fmt.Errorf("Erro ao enviar captura: %s", err)
	}

	return nil
}

func logSnapshot(camera Camera, snapshotURL string, accessToken AccessToken) {
	initialTime := time.Now()

	log.Printf("Realizando a captura da camera: %s\n", camera.ID)

	err := processSnapshot(camera.RTSP_URL, snapshotURL, accessToken)
	if err != nil {
		log.Printf("Erro ao realizar captura da camera '%s': %s\n", camera.ID, err)
	} else {
		log.Println("Captura realizada com sucesso")
	}

	log.Printf(
		"Tempo de captura da camera '%s': %.2fs\n",
		camera.ID,
		time.Since(initialTime).Seconds(),
	)
}

func runCameraSnapshot(
	ctx context.Context,
	cameraURL string,
	camera Camera,
	accessToken AccessToken,
) {
	log.Printf("Iniciando captura da camera: %s\n", camera.ID)

	defaultInterval := time.Second * time.Duration(camera.UpdateInterval)
	ticker := time.NewTicker(defaultInterval)
	snapshotURL := fmt.Sprintf("%s/%s/snapshot", cameraURL, camera.ID)

	logSnapshot(camera, snapshotURL, accessToken)

	for {
		select {
		case <-ctx.Done():
			log.Printf("Finalizando a captura da camera: %s\n", camera.ID)
			return

		case <-ticker.C:
			logSnapshot(camera, snapshotURL, accessToken)
		}
	}
}

func getCameras(cameraURL string, accessToken AccessToken) ([]Camera, error) {
	type apiData struct {
		Items []Camera `json:"items"`
		Total int      `json:"total"`
		Page  int      `json:"page"`
		Size  int      `json:"size"`
		Pages int      `json:"pages"`
	}
	data := apiData{}

	err := httpGet(cameraURL, accessToken, &data)
	if err != nil {
		return []Camera{}, fmt.Errorf("Error getting cameras: %w", err)
	}

	return data.Items, err
}

func runCameras(
	ctx context.Context,
	wg *sync.WaitGroup,
	agentURL string,
	cameraURL string,
	credentials OIDCClientCredentials,
) (time.Duration, error) {
	accessToken, err := getAccessToken(credentials)
	if err != nil {
		return time.Second, fmt.Errorf("Error getting access token: %s\n", err)
	}

	cameras, err := getCameras(agentURL, accessToken)
	if err != nil {
		return time.Second, fmt.Errorf("Error getting cameras details: %w", err)
	}

	for _, camera := range cameras {
		camera := camera
		wg.Add(1)
		go func() {
			runCameraSnapshot(ctx, cameraURL, camera, accessToken)
			wg.Done()
		}()
	}

	return time.Duration(accessToken.ExpiresIn/2) * time.Second, nil
}

func sendHeartbeat(heartbeatURL string, credentials OIDCClientCredentials, healthy bool) error {
	accessToken, err := getAccessToken(credentials)
	if err != nil {
		return fmt.Errorf("Error getting access token: %s\n", err)
	}

	rawdata := struct {
		Healthy bool `json:"healthy"`
	}{
		Healthy: healthy,
	}

	data, err := json.Marshal(rawdata)
	if err != nil {
		return fmt.Errorf("Error creating JSON body: %w", err)
	}

	_, err = httpPost(heartbeatURL, accessToken, "application/json", bytes.NewReader(data))

	return err
}

func main() {
	config, err := getConfig()
	if err != nil {
		log.Printf("%s", fmt.Errorf("error getting config: %w", err))
		return
	}

	osSignal := make(chan os.Signal, 1)
	log.Println("Esperando sinal de interrupção")
	signal.Notify(osSignal, syscall.SIGINT, syscall.SIGHUP, syscall.SIGTERM)

	wg := sync.WaitGroup{}
	ticker := time.NewTicker(config.heartbeat)

	for {
		ctxCameras, cancelCameras := context.WithCancel(context.Background())

		expires, err := runCameras(
			ctxCameras,
			&wg,
			config.agentURL,
			config.cameraURL,
			config.credentials,
		)
		ticker.Reset(min(expires, config.heartbeat))
		if err != nil {
			log.Printf("Erro ao rodar as cameras: %s\n", err)
		}

		err = sendHeartbeat(config.heartbeatURL, config.credentials, err == nil)
		if err != nil {
			log.Printf("Error sending heartbeat: %s\n", err)
		}

		select {
		case <-osSignal:
			cancelCameras()
			log.Println("Esperando as capturas serem finalizadas")
			wg.Wait()
			log.Println("Capturas finalizadas com sucesso")

			return
		case <-ticker.C:
			cancelCameras()
			log.Println("Esperando as capturas serem finalizadas")
			wg.Wait()
		}
	}
}
