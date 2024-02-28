package libs

import (
	"encoding/json"
	"fmt"
	"log"
	"net/url"
	"strings"
	"sync"
	"time"
)

type OIDCClientCredentials struct {
	TokenURL string
	Username string
	Password string
	ClientID string
}

type AccessToken struct {
	accessToken string
	tokenType   string
	interval    time.Duration
	credentials OIDCClientCredentials
	m           sync.RWMutex
}

func NewAccessTokenRaw(accessToken, tokenType string, interval time.Duration) *AccessToken {
	return &AccessToken{
		accessToken: accessToken,
		tokenType:   tokenType,
		interval:    interval,
	}
}

func NewAccessToken(credentials OIDCClientCredentials, autoRenew bool) *AccessToken {
	token := &AccessToken{
		accessToken: "",
		tokenType:   "",
		interval:    time.Second,
		credentials: credentials,
		m:           sync.RWMutex{},
	}

	if autoRenew {
		go token.autoRenew()
	}

	return token
}

func (at *AccessToken) GetHeader() string {
	at.m.RLock()
	defer at.m.RUnlock()

	return at.tokenType + " " + at.accessToken
}

func (at *AccessToken) Valid() bool {
	at.m.RLock()
	defer at.m.RUnlock()

	return at.accessToken != "" && at.tokenType != ""
}

func (at *AccessToken) Renew() error {
	data := url.Values{
		"grant_type": {"client_credentials"},
		"client_id":  {at.credentials.ClientID},
		"username":   {at.credentials.Username},
		"password":   {at.credentials.Password},
		"scope":      {"profile"},
	}

	body, err := HTTPPost(
		at.credentials.TokenURL,
		nil,
		"application/x-www-form-urlencoded",
		strings.NewReader(data.Encode()),
	)
	if err != nil {
		return fmt.Errorf("error getting Access Token: %w", err)
	}

	accessToken := struct {
		AccessToken string `json:"access_token"`
		TokenType   string `json:"token_type"`
		ExpiresIn   int    `json:"expires_in"`
	}{}

	err = json.Unmarshal(body, &accessToken)
	if err != nil {
		return fmt.Errorf("error parsing body: %w", err)
	}

	at.m.Lock()
	at.accessToken = accessToken.AccessToken
	at.interval = time.Duration(accessToken.ExpiresIn) * time.Second * 9 / 10 //nolint:gomnd
	at.tokenType = accessToken.TokenType
	at.m.Unlock()

	return nil
}

func (at *AccessToken) autoRenew() {
	ticker := time.NewTicker(at.interval)
	defer ticker.Stop()

	for {
		err := at.Renew()
		if err != nil {
			log.Printf("error renewing Access Token: %s", err)
			ticker.Reset(time.Second)
		} else {
			ticker.Reset(at.interval)
		}

		<-ticker.C
	}
}
