package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
)

func httpGet(url string, accessToken AccessToken, body any) error {
	request, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return fmt.Errorf("error creating request: %w", err)
	}
	if accessToken.TokenType != "" && accessToken.AcsessToken != "" {
		request.Header.Add("Authorization", accessToken.TokenType+" "+accessToken.AcsessToken)
	}

	response, err := http.DefaultClient.Do(request)
	if err != nil {
		return fmt.Errorf("error making request: %w", err)
	}
	defer response.Body.Close()

	rawBody, err := io.ReadAll(response.Body)
	if err != nil {
		return fmt.Errorf("error getting request body: %w", err)
	}

	if response.StatusCode >= 300 || response.StatusCode < 200 {
		return fmt.Errorf("invalid Status Code: %d, %s", response.StatusCode, rawBody)
	}

	err = json.Unmarshal(rawBody, body)
	if err != nil {
		return fmt.Errorf("error parsing body: %w", err)
	}

	return nil
}

func httpPost(
	url string,
	accessToken AccessToken,
	contentType string,
	requestBody io.Reader,
) (string, error) {
	request, err := http.NewRequest("POST", url, requestBody)
	if err != nil {
		return "", fmt.Errorf("error creating request: %w", err)
	}
	if accessToken.TokenType != "" && accessToken.AcsessToken != "" {
		request.Header.Add("Authorization", accessToken.TokenType+" "+accessToken.AcsessToken)
	}
	request.Header.Add("Content-Type", contentType)

	response, err := http.DefaultClient.Do(request)
	if err != nil {
		return "", fmt.Errorf("error making request: %w", err)
	}
	defer response.Body.Close()

	body, err := io.ReadAll(response.Body)
	if err != nil {
		return "", fmt.Errorf("error getting response body: %w", err)
	}

	if response.StatusCode >= 300 || response.StatusCode < 200 {
		return string(body), fmt.Errorf("invalid Status Code: %d, %s", response.StatusCode, body)
	}

	return string(body), err
}

func bodyFile(filename string) (string, *bytes.Buffer, error) {
	var b bytes.Buffer
	w := multipart.NewWriter(&b)

	file, err := os.Open(filename)
	if err != nil {
		return "", nil, fmt.Errorf("error opening file: %w", err)
	}
	defer file.Close()

	fw, err := w.CreateFormFile("file", file.Name())
	if err != nil {
		return "", nil, fmt.Errorf("error creating form file")
	}

	_, err = io.Copy(fw, file)
	if err != nil {
		return "", nil, fmt.Errorf("error copying file to buffer")
	}

	w.Close()

	return w.FormDataContentType(), &b, nil
}
