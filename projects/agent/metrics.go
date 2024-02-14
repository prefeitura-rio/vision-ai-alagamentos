package main

import (
	"fmt"
	"sync"
	"time"
)

//nolint:gochecknoglobals
var defaultBucketsTime = [...]time.Duration{
	100 * time.Millisecond,
	200 * time.Millisecond,
	300 * time.Millisecond,
	400 * time.Millisecond,
	500 * time.Millisecond,
	600 * time.Millisecond,
	700 * time.Millisecond,
	800 * time.Millisecond,
	900 * time.Millisecond,
	1 * time.Second,
	2 * time.Second,
	3 * time.Second,
	4 * time.Second,
	5 * time.Second,
	6 * time.Second,
	7 * time.Second,
	8 * time.Second,
	9 * time.Second,
	10 * time.Second,
	12 * time.Second,
	14 * time.Second,
	16 * time.Second,
	18 * time.Second,
	20 * time.Second,
	22 * time.Second,
	24 * time.Second,
	26 * time.Second,
	28 * time.Second,
	30 * time.Second,
	32 * time.Second,
	35 * time.Second,
	37 * time.Second,
	40 * time.Second,
	42 * time.Second,
	45 * time.Second,
	47 * time.Second,
	50 * time.Second,
	55 * time.Second,
	60 * time.Second,
	65 * time.Second,
	70 * time.Second,
	75 * time.Second,
	80 * time.Second,
	85 * time.Second,
	90 * time.Second,
	95 * time.Second,
	100 * time.Second,
	110 * time.Second,
	120 * time.Second,
	130 * time.Second,
	140 * time.Second,
	150 * time.Second,
	160 * time.Second,
	170 * time.Second,
	180 * time.Second,
	190 * time.Second,
	200 * time.Second,
	210 * time.Second,
}

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

type errSuccess[T any] struct {
	err     T
	success T
}

type metricsAggregation struct {
	processedItems errSuccess[uint]
	timeProcessing errSuccess[time.Duration]
	mutexMetrics   *sync.RWMutex
	bucketsTimes   []time.Duration
	metrics        errSuccess[map[string]map[time.Duration]uint]
}

func newMetricsAggregation() *metricsAggregation {
	return &metricsAggregation{
		processedItems: errSuccess[uint]{0, 0},
		timeProcessing: errSuccess[time.Duration]{0, 0},
		mutexMetrics:   &sync.RWMutex{},
		metrics: errSuccess[map[string]map[time.Duration]uint]{
			err:     map[string]map[time.Duration]uint{},
			success: map[string]map[time.Duration]uint{},
		},
		bucketsTimes: defaultBucketsTime[:],
	}
}

func (m *metricsAggregation) findBucket(current time.Duration) time.Duration {
	for index, bucket := range m.bucketsTimes {
		if bucket >= current {
			return m.bucketsTimes[max(index-1, 0)]
		}
	}

	return m.bucketsTimes[len(m.bucketsTimes)-1]
}

func (m *metricsAggregation) createKey(success bool, key string) {
	if success {
		m.metrics.success[key] = map[time.Duration]uint{}
		for _, bucket := range m.bucketsTimes {
			m.metrics.success[key][bucket] = 0
		}
	} else {
		m.metrics.err[key] = map[time.Duration]uint{}
		for _, bucket := range m.bucketsTimes {
			m.metrics.err[key][bucket] = 0
		}
	}
}

func (m *metricsAggregation) addMetrics(allMetrics []*metrics) {
	m.mutexMetrics.Lock()
	defer m.mutexMetrics.Unlock()

	for _, rawMetrics := range allMetrics {
		metrics := map[string]time.Duration{}

		for index := range len(rawMetrics.order) {
			key, value := rawMetrics.diff(index)
			metrics[key] = m.findBucket(value)
		}

		key, value := rawMetrics.total()
		metrics[key] = m.findBucket(value)

		if rawMetrics.success {
			m.processedItems.success++
			m.timeProcessing.success += value

			for key, value := range metrics {
				if _, ok := m.metrics.success[key]; !ok {
					m.createKey(rawMetrics.success, key)
				}

				m.metrics.success[key][value]++
			}
		} else {
			m.processedItems.err++
			m.timeProcessing.err += value

			for key, value := range metrics {
				if _, ok := m.metrics.err[key]; !ok {
					m.createKey(rawMetrics.success, key)
				}

				m.metrics.err[key][value]++
			}
		}
	}
}

// func (m *metricsAggregation) percentile(
// 	key string,
// 	percentile uint,
// ) (time.Duration, time.Duration) {
// 	m.mutexMetrics.RLock()
// 	defer m.mutexMetrics.RUnlock()

// 	ps := (float64(percentile)/100)*(float64(m.processedItems.success)-1) + 1
// 	pe := (float64(percentile)/100)*(float64(m.processedItems.err)-1) + 1
// 	psi, psr := math.Modf(ps)
// 	pei, per := math.Modf(pe)

// 	psl, psh := time.Duration(0), time.Duration(0)
// 	pel, peh := time.Duration(0), time.Duration(0)
// 	st, et := uint(0), uint(0)

// 	for index, bucket := range m.bucketsTimes {
// 		if _, ok := m.metrics.success[key]; ok {
// 			st += m.metrics.success[key][bucket]
// 			if float64(st) > psi && psl == 0 {
// 				if float64(st)-psi > psr {
// 					psl, psh = bucket, bucket
// 				} else {
// 					psl, psh = bucket, m.bucketsTimes[min(index+1, len(m.bucketsTimes)-1)]
// 				}
// 			}
// 		}

// 		if _, ok := m.metrics.err[key]; ok {
// 			et += m.metrics.err[key][bucket]
// 			if float64(et) > pei && pel == 0 {
// 				if float64(et)-pei > per {
// 					pel, peh = bucket, bucket
// 				} else {
// 					pel, peh = bucket, m.bucketsTimes[min(index+1, len(m.bucketsTimes)-1)]
// 				}
// 			}
// 		}

// 		if psl != 0 && pel != 0 {
// 			break
// 		}
// 	}

// 	return psl + time.Duration(psr*float64(psh-psl)), pel + time.Duration(per*float64(peh-pel))
// }

// func (m *metricsAggregation) percentiles(p uint) {
// 	m.mutexMetrics.RLock()
// 	defer m.mutexMetrics.RUnlock()

// 	keys := make([]string, 0, max(len(m.metrics.err), len(m.metrics.success)))
// 	for key := range m.metrics.success {
// 		keys = append(keys, key)
// 	}

// 	for key := range m.metrics.err {
// 		if !slices.Contains(keys, key) {
// 			keys = append(keys, key)
// 		}
// 	}

// 	slices.Sort(keys)

// 	for _, key := range keys {
// 		psuccess, perr := m.percentile(key, p)
// 		log.Printf("%s P%d success: %s err: %s", key, p, psuccess, perr)
// 	}
// }

// func (m *metricsAggregation) printPercentiles() {
// 	m.mutexMetrics.RLock()
// 	defer m.mutexMetrics.RUnlock()

// 	m.percentiles(uint(10))
// 	m.percentiles(uint(25))
// 	m.percentiles(uint(50))
// 	m.percentiles(uint(75))
// 	m.percentiles(uint(95))
// 	m.percentiles(uint(99))
// 	log.Println("processed cameras success:", m.processedItems.success)
// 	log.Printf("time processing success: %.2f", m.timeProcessing.success.Seconds())
// 	log.Printf(
// 		"avg time processing success: %.2f",
// 		m.timeProcessing.success.Seconds()/float64(m.processedItems.success),
// 	)
// 	log.Println("processed cameras err:", m.processedItems.err)
// 	log.Printf("time processing err: %.2f", m.timeProcessing.err.Seconds())
// 	log.Printf(
// 		"avg time processing err: %.2f",
// 		m.timeProcessing.err.Seconds()/float64(m.processedItems.err),
// 	)
// }
