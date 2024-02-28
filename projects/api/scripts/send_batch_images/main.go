package main

import (
	"bytes"
	"context"
	"crypto/md5"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"image/jpeg"
	"image/png"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"cloud.google.com/go/storage"
	"github.com/prefeitura-rio/vision-ai/libs"
	"google.golang.org/api/iterator"
)

const (
	timeout           = time.Minute
	requestsPerMinute = 45
	filename          = "snapshots-id.txt"
)

func downloadImage(
	ctx context.Context,
	bucket *storage.BucketHandle,
	object string,
) ([]byte, error) {
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	reader, err := bucket.Object(object).NewReader(ctx)
	if err != nil {
		return nil, fmt.Errorf("error creating object reader: %w", err)
	}
	defer reader.Close()

	data, err := io.ReadAll(reader)
	if err != nil {
		return nil, fmt.Errorf("error reading object: %w", err)
	}

	return data, nil
}

func imageToPng(image []byte) ([]byte, error) {
	contentType := http.DetectContentType(image)

	switch contentType {
	case "image/png":
		return image, nil
	case "image/jpeg":
		img, err := jpeg.Decode(bytes.NewReader(image))
		if err != nil {
			return nil, fmt.Errorf("unable to decode jpeg: %w", err)
		}

		buf := new(bytes.Buffer)
		if err := png.Encode(buf, img); err != nil {
			return nil, fmt.Errorf("unable to encode png: %w", err)
		}

		return buf.Bytes(), nil
	}

	return nil, fmt.Errorf("unable to convert %#v to png", contentType)
}

func run(
	ctx context.Context,
	bucket *storage.BucketHandle,
	object string,
	accessToken *libs.AccessToken,
	snapshotURL string,
) (string, error) {
	image, err := downloadImage(ctx, bucket, object)
	if err != nil {
		return "", fmt.Errorf("error downloading file: %w", err)
	}

	image, err = imageToPng(image)
	if err != nil {
		return "", fmt.Errorf("error converting image: %w", err)
	}

	hashSum := md5.Sum(image)
	hash := base64.StdEncoding.EncodeToString(hashSum[:])
	contentLength := len(image)
	data := struct {
		HashMD5       string `json:"hash_md5"`
		ContentLength int    `json:"content_length"`
	}{
		HashMD5:       hash,
		ContentLength: contentLength,
	}

	body, err := json.Marshal(data)
	if err != nil {
		return "", fmt.Errorf("error creating snapshot body: %w", err)
	}

	response, err := libs.HTTPPost(
		snapshotURL,
		accessToken,
		"application/json",
		bytes.NewReader(body),
	)
	if err != nil {
		return "", fmt.Errorf("error creating snapshot: %w", err)
	}

	snapshot := struct {
		ID       string `json:"id"`
		CameraID string `json:"camera_id"`
		ImageURL string `json:"image_url"`
	}{}

	err = json.Unmarshal(response, &snapshot)
	if err != nil {
		return "", fmt.Errorf("error parsing body: %w", err)
	}

	headers := map[string]string{
		"Content-Type": "image/png",
		"Content-MD5":  hash,
	}

	_, err = libs.HTTPPut(snapshot.ImageURL, headers, bytes.NewReader(image))
	if err != nil {
		return "", fmt.Errorf("error sending snapshot: %w", err)
	}

	preditcURL := snapshotURL + "/" + snapshot.ID + "/predict"

	_, err = libs.HTTPPost(preditcURL, accessToken, "application/json", nil)
	if err != nil {
		return "", fmt.Errorf("error creating predictions: %w", err)
	}

	return snapshot.ID, nil
}

func main() {
	ctx := context.Background()
	envs := []string{"API_BASE_URL", "API_USERNAME", "API_PASSWORD", "BUCKET_NAME", "BUCKET_PREFIX"}

	empty := []string{}

	for _, env := range envs {
		if os.Getenv(env) == "" {
			empty = append(empty, env)
		}
	}

	if len(empty) != 0 {
		log.Panicln("The following environment variables must be set:", strings.Join(empty, ", "))
	}

	bucketName := os.Getenv("BUCKET_NAME")
	bucketPrefix := os.Getenv("BUCKET_PREFIX")
	baseURL := os.Getenv("API_BASE_URL")
	snapshotURL := baseURL + "/cameras/0001/snapshots"
	credentials := libs.OIDCClientCredentials{
		TokenURL: baseURL + "/auth/token",
		Username: os.Getenv("API_USERNAME"),
		Password: os.Getenv("API_PASSWORD"),
	}
	accessToken := libs.NewAccessToken(credentials, true)

	file, err := os.Create(filename)
	if err != nil {
		log.Panicf("Error creating file: %s", err)
	}
	defer file.Close()

	client, err := storage.NewClient(ctx)
	if err != nil {
		log.Panicf("Error creating storage client: %s", err)
	}
	defer client.Close()

	objectNames := []string{}
	query := &storage.Query{Prefix: bucketPrefix}
	bucket := client.Bucket(bucketName)
	it := bucket.Objects(ctx, query)
	start := time.Now()

	for {
		attrs, err := it.Next()
		if errors.Is(err, iterator.Done) {
			break
		}

		if err != nil {
			log.Panic(err)
		}

		contentType := attrs.ContentType
		if contentType == "image/png" || contentType == "image/jpeg" {
			objectNames = append(objectNames, attrs.Name)
		}
	}

	log.Printf("getting time: %.2fs", time.Since(start).Seconds())
	log.Printf("%d snapshots to send", len(objectNames))

	workers := sync.WaitGroup{}
	writers := sync.WaitGroup{}

	for !accessToken.Valid() {
		time.Sleep(time.Second)
	}

	start = time.Now()
	ticker := time.NewTicker(time.Minute)
	snapshotIDs := make(chan string, requestsPerMinute)

	writers.Add(1)

	go func() {
		defer writers.Done()

		for snapshotID := range snapshotIDs {
			_, err := file.WriteString(snapshotID + "\n")
			if err != nil {
				log.Panicf("error writing file: %s", err)
			}
		}
	}()

	for index, object := range objectNames {
		objectName := object

		workers.Add(1)

		go func() {
			defer workers.Done()

			snapshotID, err := run(ctx, bucket, objectName, accessToken, snapshotURL)
			if err != nil {
				log.Printf("error running worker: %s", err)
			}

			snapshotIDs <- snapshotID
		}()

		// only send requestsPerMinute, dont consume all Vertex AI API Quota
		if (index+1)%requestsPerMinute == 0 {
			log.Println("waiting 1 minute")
			workers.Wait()
			<-ticker.C
		}
	}

	workers.Wait()
	close(snapshotIDs)

	log.Printf("running time: %.2fs", time.Since(start).Seconds())
}
