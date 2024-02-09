package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/url"
	"strings"
	"sync"
	"time"
)

type AccessToken struct {
	accessToken string
	tokenType   string
	interval    time.Duration
	credentials OIDCClientCredentials
	m           sync.RWMutex
}

func NewAccessToken(credentials OIDCClientCredentials, autoRenew bool) *AccessToken {
	at := &AccessToken{
		accessToken: "",
		tokenType:   "",
		interval:    time.Second,
		credentials: credentials,
		m:           sync.RWMutex{},
	}

	if autoRenew {
		go at.autoRenew()
	}

	return at
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

	body, err := httpPost(
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
	at.interval = time.Duration(accessToken.ExpiresIn) * time.Second * 8 / 10
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
