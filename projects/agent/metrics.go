package main

import (
	"log"
	"math"
	"slices"
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

const totalLabel = "total"

type metricData struct {
	label    string
	duration time.Duration
}

type metrics struct {
	data         []metricData
	startTime    time.Time
	previousTime time.Time
	currentLabel string
	success      bool
	running      bool
	total        time.Duration
}

func newMetrics() *metrics {
	now := time.Now()
	metrics := &metrics{
		data:         []metricData{},
		startTime:    now,
		previousTime: time.Now(),
		currentLabel: "init",
		success:      false,
		running:      true,
	}

	return metrics
}

func (metrics *metrics) add(label string) {
	now := time.Now()
	key := metrics.currentLabel + "__" + label
	metrics.data = append(metrics.data, metricData{key, now.Sub(metrics.previousTime)})
	metrics.previousTime = now
	metrics.currentLabel = label
}

func (metrics *metrics) stop(success bool) {
	if metrics.running {
		metrics.add("final")

		metrics.total = time.Since(metrics.startTime)
		metrics.running = false
		metrics.success = success
	}
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
	metrics        map[string]map[time.Duration]errSuccess[uint]
}

func newMetricsAggregation() *metricsAggregation {
	aggregation := &metricsAggregation{
		processedItems: errSuccess[uint]{0, 0},
		timeProcessing: errSuccess[time.Duration]{0, 0},
		mutexMetrics:   &sync.RWMutex{},
		metrics:        map[string]map[time.Duration]errSuccess[uint]{},
		bucketsTimes:   defaultBucketsTime[:],
	}

	aggregation.createKey(totalLabel)

	return aggregation
}

func (a *metricsAggregation) findBucket(current time.Duration) time.Duration {
	for index, bucket := range a.bucketsTimes {
		if bucket >= current {
			return a.bucketsTimes[max(index-1, 0)]
		}
	}

	return a.bucketsTimes[len(a.bucketsTimes)-1]
}

func (a *metricsAggregation) createKey(key string) {
	a.metrics[key] = map[time.Duration]errSuccess[uint]{}
	for _, bucket := range a.bucketsTimes {
		a.metrics[key][bucket] = errSuccess[uint]{
			err:     0,
			success: 0,
		}
	}
}

func (a *metricsAggregation) addMetrics(allMetrics []*metrics) {
	for _, rawMetrics := range allMetrics {
		rawMetrics.stop(true)
	}

	a.mutexMetrics.Lock()
	defer a.mutexMetrics.Unlock()

	for _, rawMetrics := range allMetrics {
		for _, metricData := range rawMetrics.data {
			key := metricData.label
			bucket := a.findBucket(metricData.duration)

			metrics, ok := a.metrics[key]
			if !ok {
				a.createKey(key)
				metrics = a.metrics[key]
			}

			count := metrics[bucket]

			if rawMetrics.success {
				count.success++
			} else {
				count.err++
			}

			a.metrics[key][bucket] = count
		}

		totalBucket := a.findBucket(rawMetrics.total)
		total := a.metrics[totalLabel][totalBucket]

		if rawMetrics.success {
			a.processedItems.success++
			a.timeProcessing.success += rawMetrics.total
			total.success++
		} else {
			a.processedItems.err++
			a.timeProcessing.err += rawMetrics.total
			total.err++
		}

		a.metrics[totalLabel][totalBucket] = total
	}
}

func (a *metricsAggregation) percentile(
	key string,
	limit uint,
) (time.Duration, time.Duration) {
	a.mutexMetrics.RLock()
	defer a.mutexMetrics.RUnlock()

	qtSuccess := (float64(limit)/100)*(float64(a.processedItems.success)-1) + 1 //nolint:gomnd
	qtSuccessInteger, qtSuccessRemainder := math.Modf(qtSuccess)
	successLow, successHigh := time.Duration(0), time.Duration(0)
	successCount := uint(0)

	qtErr := (float64(limit)/100)*(float64(a.processedItems.err)-1) + 1 //nolint:gomnd
	qtErrInteger, qtErrRemainder := math.Modf(qtErr)
	errLow, errHigh := time.Duration(0), time.Duration(0)
	errCount := uint(0)

	for index, bucket := range a.bucketsTimes {
		successCount += a.metrics[key][bucket].success
		if float64(successCount) > qtSuccessInteger && successLow == 0 {
			if float64(successCount)-qtSuccessInteger > qtSuccessRemainder {
				successLow, successHigh = bucket, bucket
			} else {
				successLow, successHigh = bucket, a.bucketsTimes[min(index+1, len(a.bucketsTimes)-1)]
			}
		}

		errCount += a.metrics[key][bucket].err
		if float64(errCount) > qtErrInteger && errLow == 0 {
			if float64(errCount)-qtErrInteger > qtErrRemainder {
				errLow, errHigh = bucket, bucket
			} else {
				errLow, errHigh = bucket, a.bucketsTimes[min(index+1, len(a.bucketsTimes)-1)]
			}
		}

		if successLow != 0 && errLow != 0 {
			break
		}
	}

	success := successLow + time.Duration(qtSuccessRemainder*float64(successHigh-successLow))
	err := errLow + time.Duration(qtErrRemainder*float64(errHigh-errLow))

	return success, err
}

func (a *metricsAggregation) percentiles(limit uint) {
	a.mutexMetrics.RLock()
	defer a.mutexMetrics.RUnlock()

	keys := make([]string, 0, len(a.metrics))
	for key := range a.metrics {
		keys = append(keys, key)
	}

	slices.Sort(keys)

	for _, key := range keys {
		psuccess, perr := a.percentile(key, limit)
		log.Printf("%s P%d success: %s err: %s", key, limit, psuccess, perr)
	}
}

func (a *metricsAggregation) printPercentiles() {
	a.mutexMetrics.RLock()
	defer a.mutexMetrics.RUnlock()

	a.percentiles(uint(10)) //nolint:gomnd
	a.percentiles(uint(25)) //nolint:gomnd
	a.percentiles(uint(50)) //nolint:gomnd
	a.percentiles(uint(75)) //nolint:gomnd
	a.percentiles(uint(95)) //nolint:gomnd
	a.percentiles(uint(99)) //nolint:gomnd
	log.Println("processed cameras success:", a.processedItems.success)
	log.Printf("time processing success: %.2fs", a.timeProcessing.success.Seconds())
	log.Printf(
		"avg time processing success: %.2fs",
		a.timeProcessing.success.Seconds()/float64(a.processedItems.success),
	)
	log.Println("processed cameras err:", a.processedItems.err)
	log.Printf("time processing err: %.2fs", a.timeProcessing.err.Seconds())
	log.Printf(
		"avg time processing err: %.2fs",
		a.timeProcessing.err.Seconds()/float64(a.processedItems.err),
	)
}
