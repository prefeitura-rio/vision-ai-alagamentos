package main

import (
	"encoding/json"
	"fmt"
	"image"
	"image/png"
	"io"
	"mime/multipart"
	"net/http"
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

func bodyImage(id string, img image.Image) (string, *io.PipeReader) {
	ir, iw := io.Pipe()

	go func() {
		err := png.Encode(iw, img)
		if err != nil {
			iw.CloseWithError(err)
		}
		iw.CloseWithError(nil)
	}()

	pr, pw := io.Pipe()
	writer := multipart.NewWriter(pw)
	go func() {
		part, err := writer.CreateFormFile("file", id+".png")
		if err != nil {
			pw.CloseWithError(err)
			ir.CloseWithError(err)
			return
		}
		_, err = io.Copy(part, ir)
		if err != nil {
			pw.CloseWithError(err)
			ir.CloseWithError(err)
			return
		}

		err = writer.Close()
		pw.CloseWithError(err)
		ir.CloseWithError(err)
	}()

	return writer.FormDataContentType(), pr
}
