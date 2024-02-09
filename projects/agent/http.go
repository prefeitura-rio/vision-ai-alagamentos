package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

func httpGet(url string, accessToken *AccessToken, body any) error {
	request, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return fmt.Errorf("error creating request: %w", err)
	}
	if accessToken != nil {
		request.Header.Add("Authorization", accessToken.GetHeader())
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
	accessToken *AccessToken,
	contentType string,
	requestBody io.Reader,
) ([]byte, error) {
	request, err := http.NewRequest("POST", url, requestBody)
	if err != nil {
		return []byte{}, fmt.Errorf("error creating request: %w", err)
	}
	if accessToken != nil {
		request.Header.Add("Authorization", accessToken.GetHeader())
	}
	request.Header.Add("Content-Type", contentType)

	response, err := http.DefaultClient.Do(request)
	if err != nil {
		return []byte{}, fmt.Errorf("error making request: %w", err)
	}
	defer response.Body.Close()

	body, err := io.ReadAll(response.Body)
	if err != nil {
		return []byte{}, fmt.Errorf("error getting response body: %w", err)
	}

	if response.StatusCode >= 300 || response.StatusCode < 200 {
		return body, fmt.Errorf("invalid Status Code: %d, %s", response.StatusCode, body)
	}

	return body, err
}

func httpPut(
	url string,
	headers map[string]string,
	requestBody io.Reader,
) ([]byte, error) {
	request, err := http.NewRequest("PUT", url, requestBody)
	if err != nil {
		return []byte{}, fmt.Errorf("error creating request: %w", err)
	}
	for key, value := range headers {
		request.Header.Add(key, value)
	}

	response, err := http.DefaultClient.Do(request)
	if err != nil {
		return []byte{}, fmt.Errorf("error making request: %w", err)
	}
	defer response.Body.Close()

	body, err := io.ReadAll(response.Body)
	if err != nil {
		return []byte{}, fmt.Errorf("error getting response body: %w", err)
	}

	if response.StatusCode >= 300 || response.StatusCode < 200 {
		return body, fmt.Errorf("invalid Status Code: %d, %s", response.StatusCode, body)
	}

	return body, err
}
