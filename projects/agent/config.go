package main

import (
	"crypto/aes"
	"crypto/cipher"
	"encoding/base64"
	"fmt"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/prefeitura-rio/vision-ai/libs"
)

var (
	errGreaterThanZero       = fmt.Errorf("must be greater than zero")
	errDecryptingKey         = fmt.Errorf("error decrypting key")
	errInvalidInfisicalToken = fmt.Errorf("invalid infisical token")
	errEmptyVariables        = fmt.Errorf("empty variables")
)

type infisicalConfig struct {
	url         string
	token       string
	secretKey   string
	environment string
}

type config struct {
	apiBaseURL        string
	agentID           string
	credentials       libs.OIDCClientCredentials
	heartbeat         time.Duration
	parallelSnapshots int
}

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
	//nolint:tagliatelle
	type ServiceToken struct {
		EncryptedKey string `json:"encryptedKey"`
		IV           string `json:"iv"`
		Tag          string `json:"tag"`
		WorkspaceID  string `json:"workspace"`
	}

	//nolint:tagliatelle
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
	token := libs.NewAccessTokenRaw(config.token, "Bearer", time.Second)
	serviceToken := ServiceToken{}
	secretsRaw := SecretsRaw{}
	secrets := map[string]string{}

	err := libs.HTTPGet(serviceTokenURL, token, &serviceToken)
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
		return secrets, errDecryptingKey
	}

	secretURL := fmt.Sprintf(
		"%s/api/v3/secrets?environment=%s&workspaceId=%s",
		config.url,
		config.environment,
		serviceToken.WorkspaceID,
	)

	err = libs.HTTPGet(secretURL, token, &secretsRaw)
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
		"API_BASE_URL",
	}
	emptyEnvs := []string{}

	for _, env := range envNames {
		if value := os.Getenv(env); value == "" {
			emptyEnvs = append(emptyEnvs, env)
		}
	}

	if len(emptyEnvs) > 0 {
		return config{}, fmt.Errorf(
			"environment: %w: %s",
			errEmptyVariables,
			strings.Join(emptyEnvs, ", "),
		)
	}

	regex := regexp.MustCompile(`^(st\.[a-f0-9]+\.[a-f0-9]+)\.(?P<secret>[a-f0-9]+)$`)
	match := (regex.FindStringSubmatch(os.Getenv("INFISICAL_TOKEN")))
	secretIndex := regex.SubexpIndex("secret")

	if secretIndex != 2 { //nolint:gomnd
		return config{}, errInvalidInfisicalToken
	}

	infisicalConfig := infisicalConfig{
		url:         os.Getenv("INFISICAL_ADDRESS"),
		token:       os.Getenv("INFISICAL_TOKEN"),
		secretKey:   match[secretIndex],
		environment: os.Getenv("INFISICAL_ENVIRONMENT"),
	}

	secrets, err := getInfisicalSecrets(infisicalConfig)
	if err != nil {
		return config{}, fmt.Errorf("error getting infisical secrets: %w", err)
	}

	secretsNames := []string{
		"OIDC_TOKEN_URL",
		"OIDC_USERNAME",
		"OIDC_PASSWORD",
		"HEARTBEAT_SECONDS",
		"PARALLEL_SNAPSHOTS",
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
			"infisical: %w: %s",
			errEmptyVariables,
			strings.Join(emptySecrets, ", "),
		)
	}

	heartbeatSeconds, err := strconv.ParseInt(secrets["HEARTBEAT_SECONDS"], 10, 0)
	if err != nil {
		return config{}, fmt.Errorf("error convert HEARTBEAT_SECONDS: %w", err)
	}

	if heartbeatSeconds <= 0 {
		return config{}, fmt.Errorf("HEARTBEAT_SECONDS %w", errGreaterThanZero)
	}

	credentials := libs.OIDCClientCredentials{
		TokenURL: secrets["OIDC_TOKEN_URL"],
		Username: secrets["OIDC_USERNAME"],
		Password: secrets["OIDC_PASSWORD"],
	}

	accessToken := libs.NewAccessToken(credentials, false)

	err = accessToken.Renew()
	if err != nil {
		return config{}, fmt.Errorf("error getting access token: %w", err)
	}

	apiBaseURL := os.Getenv("API_BASE_URL")
	api := struct {
		ID string `json:"id"`
	}{}

	err = libs.HTTPGet(apiBaseURL+"/agents/me", accessToken, &api)
	if err != nil {
		return config{}, fmt.Errorf("error getting agent ID: %w", err)
	}

	parallelSnapshots, err := strconv.ParseInt(secrets["PARALLEL_SNAPSHOTS"], 10, 0)
	if err != nil {
		return config{}, fmt.Errorf("error convert PARALLEL_SNAPSHOTS: %w", err)
	}

	if parallelSnapshots <= 0 {
		return config{}, fmt.Errorf("PARALLEL_SNAPSHOTS %w", errGreaterThanZero)
	}

	config := config{
		apiBaseURL:        apiBaseURL,
		agentID:           api.ID,
		credentials:       credentials,
		heartbeat:         time.Second * time.Duration(heartbeatSeconds),
		parallelSnapshots: int(parallelSnapshots),
	}

	return config, nil
}
