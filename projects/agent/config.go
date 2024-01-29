package main

import (
	"context"
	"crypto/aes"
	"crypto/cipher"
	"encoding/base64"
	"fmt"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"
)

func decrypt(key, nonce, tag, cipherText string) (string, error) {
	nonceb64, err := base64.StdEncoding.DecodeString(nonce)
	if err != nil {
		return "", fmt.Errorf("error decoding nonce: %w", err)
	}
	tagb64, err := base64.StdEncoding.DecodeString(tag)
	if err != nil {
		return "", fmt.Errorf("error decoding tag: %w", err)
	}
	cipherTextb64, err := base64.StdEncoding.DecodeString(cipherText)
	if err != nil {
		return "", fmt.Errorf("error decoding cipher text: %w", err)
	}

	block, err := aes.NewCipher([]byte(key))
	if err != nil {
		return "", fmt.Errorf("error creating cipher block: %w", err)
	}
	aesgcm, err := cipher.NewGCMWithNonceSize(block, len(nonceb64))
	if err != nil {
		return "", fmt.Errorf("error creating cipher: %w", err)
	}

	plaintext, err := aesgcm.Open(nil, nonceb64, append(cipherTextb64, tagb64...), nil)
	if err != nil {
		return "", fmt.Errorf("error decrypting cipher text: %w", err)
	}

	return string(plaintext), err
}

func getInfisicalSecrets(config infisicalConfig) (map[string]string, error) {
	type ServiceToken struct {
		EncryptedKey string `json:"encryptedKey"`
		IV           string `json:"iv"`
		Tag          string `json:"tag"`
		WorkspaceID  string `json:"workspace"`
	}

	type SecretRaw struct {
		SecretKeyCiphertext   string `json:"secretKeyCiphertext"`
		SecretKeyIV           string `json:"secretKeyIV"`
		SecretKeyTag          string `json:"secretKeyTag"`
		SecretValueCiphertext string `json:"secretValueCiphertext"`
		SecretValueIV         string `json:"secretValueIV"`
		SecretValueTag        string `json:"secretValueTag"`
	}

	type SecretsRaw struct {
		Secrets []SecretRaw `json:"secrets"`
	}

	serviceTokenURL := config.url + "/api/v2/service-token/"
	token := AccessToken{
		AcsessToken: config.token,
		TokenType:   "Bearer",
		ExpiresIn:   300,
	}
	serviceToken := ServiceToken{}
	secretsRaw := SecretsRaw{}
	secrets := map[string]string{}

	err := httpGet(context.Background(), serviceTokenURL, token, &serviceToken)
	if err != nil {
		return secrets, fmt.Errorf("error getting service token: %w", err)
	}

	projectKey, err := decrypt(
		config.secretKey,
		serviceToken.IV,
		serviceToken.Tag,
		serviceToken.EncryptedKey,
	)
	if err != nil {
		return secrets, fmt.Errorf("error decrypting project key")
	}

	secretURL := fmt.Sprintf(
		"%s/api/v3/secrets?environment=%s&workspaceId=%s",
		config.url,
		config.environment,
		serviceToken.WorkspaceID,
	)
	err = httpGet(context.Background(), secretURL, token, &secretsRaw)
	if err != nil {
		return secrets, fmt.Errorf("error getting secrets: %w", err)
	}

	for _, secret := range secretsRaw.Secrets {
		key, err := decrypt(
			projectKey,
			secret.SecretKeyIV,
			secret.SecretKeyTag,
			secret.SecretKeyCiphertext,
		)
		if err != nil {
			return secrets, fmt.Errorf("error getting key: %w", err)
		}

		value, err := decrypt(
			projectKey,
			secret.SecretValueIV,
			secret.SecretValueTag,
			secret.SecretValueCiphertext,
		)
		if err != nil {
			return secrets, fmt.Errorf("error getting key: %w", err)
		}

		secrets[key] = value
	}

	return secrets, nil
}

func getConfig() (config, error) {
	envNames := []string{
		"INFISICAL_ADDRESS",
		"INFISICAL_TOKEN",
		"INFISICAL_ENVIRONMENT",
		"AGENT_URL",
		"CAMERA_URL",
		"HEARTBEAT_URL",
	}
	emptyEnvs := []string{}
	for _, env := range envNames {
		if value := os.Getenv(env); value == "" {
			emptyEnvs = append(emptyEnvs, env)
		}
	}

	if len(emptyEnvs) > 0 {
		return config{}, fmt.Errorf(
			"The following environment is empty: %s",
			strings.Join(emptyEnvs, ", "),
		)
	}

	regex := regexp.MustCompile(`^(st\.[a-f0-9]+\.[a-f0-9]+)\.(?P<secret>[a-f0-9]+)$`)
	match := (regex.FindStringSubmatch(os.Getenv("INFISICAL_TOKEN")))
	secretIndex := regex.SubexpIndex("secret")
	if secretIndex != 2 {
		return config{}, fmt.Errorf("invalid infisical token")
	}

	infisicalConfig := infisicalConfig{
		url:         os.Getenv("INFISICAL_ADDRESS"),
		token:       os.Getenv("INFISICAL_TOKEN"),
		secretKey:   match[secretIndex],
		environment: os.Getenv("INFISICAL_ENVIRONMENT"),
	}

	secrets, err := getInfisicalSecrets(infisicalConfig)
	if err != nil {
		return config{}, fmt.Errorf("error geting infisical secrets: %w", err)
	}

	secretsNames := []string{
		"OIDC_TOKEN_URL",
		"OIDC_USERNAME",
		"OIDC_PASSWORD",
		"OIDC_CLIENT_ID",
	}
	emptySecrets := []string{}

	for _, secret := range secretsNames {
		value, ok := secrets[secret]
		if !ok || value == "" {
			emptySecrets = append(emptySecrets, secret)
		}
	}

	if len(emptySecrets) > 0 {
		return config{}, fmt.Errorf(
			"The following infisical secrets is empty: %s",
			strings.Join(emptySecrets, ", "),
		)
	}

	heartbeatSeconds, err := strconv.ParseInt(secrets["HEARTBEAT_SECONDS"], 10, 0)
	if err != nil {
		return config{}, fmt.Errorf("error convert HEARTBEAT_SECONDS: %w", err)
	}
	if heartbeatSeconds <= 0 {
		return config{}, fmt.Errorf("HEARTBEAT_SECONDS must be greater than zero")
	}

	config := config{
		agentURL:     os.Getenv("AGENT_URL"),
		cameraURL:    os.Getenv("CAMERA_URL"),
		heartbeatURL: os.Getenv("HEARTBEAT_URL"),
		credentials: OIDCClientCredentials{
			TokenURL: secrets["OIDC_TOKEN_URL"],
			Username: secrets["OIDC_USERNAME"],
			Password: secrets["OIDC_PASSWORD"],
			ClientID: secrets["OIDC_CLIENT_ID"],
		},
		heartbeat: time.Second * time.Duration(heartbeatSeconds),
	}
	return config, nil
}
