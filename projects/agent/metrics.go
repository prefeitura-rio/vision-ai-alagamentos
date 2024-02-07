package main

import (
	"fmt"
	"time"
)

type metrics struct {
	data    map[string]time.Time
	order   []string
	success bool
}

func newMetrics() *metrics {
	metrics := &metrics{
		data:    map[string]time.Time{},
		order:   []string{},
		success: false,
	}
	metrics.add("init")

	return metrics
}

func (metrics *metrics) add(label string) {
	metrics.data[label] = time.Now()
	metrics.order = append(metrics.order, label)
}

func (metrics *metrics) final() {
	metrics.add("final")
}

func (metrics *metrics) diff(index int) (string, time.Duration) {
	previous := metrics.order[index-1]
	current := metrics.order[index]
	key := fmt.Sprintf("%d__%s__%s", index, previous, current)
	value := metrics.data[current].Sub(metrics.data[previous])
	return key, value
}

func (metrics *metrics) total() (string, time.Duration) {
	if len(metrics.order) == 0 {
		return "", 0
	}
	previous := metrics.order[0]
	current := metrics.order[len(metrics.order)-1]
	key := fmt.Sprintf("%d__%s__%s", len(metrics.order), previous, current)
	value := metrics.data[current].Sub(metrics.data[previous])
	return key, value
}
