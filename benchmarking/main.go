package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	compute "cloud.google.com/go/compute/apiv1"
	"cloud.google.com/go/compute/apiv1/computepb"
	"google.golang.org/api/iterator"
)

const tickerDuration = 10 * time.Second

func getZones(projectID string) (map[string]string, error) {
	ctx := context.Background()

	client, err := compute.NewZonesRESTClient(ctx)
	if err != nil {
		return nil, fmt.Errorf("error creating zone client: %w", err)
	}
	defer client.Close()

	zones := map[string]string{}
	req := &computepb.ListZonesRequest{
		Project: projectID,
	}
	it := client.List(ctx, req)

	for {
		resp, err := it.Next()
		if errors.Is(err, iterator.Done) {
			break
		}

		if err != nil {
			return nil, fmt.Errorf("error getting zone: %w", err)
		}

		zones[resp.GetSelfLink()] = resp.GetName()
	}

	return zones, nil
}

func resumeInstances(
	ctx context.Context,
	waitGroup *sync.WaitGroup,
	instanceClient *compute.InstancesClient,
	zones map[string]string,
	projectID string,
) {
	filter := "(name eq '.*vision-ai-benchmarking.*') (status eq TERMINATED)"
	reqInstances := &computepb.AggregatedListInstancesRequest{
		Project: projectID,
		Filter:  &filter,
	}
	instances := []*computepb.Instance{}
	it := instanceClient.AggregatedList(ctx, reqInstances)

	for {
		resp, err := it.Next()
		if errors.Is(err, iterator.Done) {
			break
		}

		if err != nil {
			log.Printf("Error getting instances: %s", err)
		} else {
			instances = append(instances, resp.Value.GetInstances()...)
		}
	}

	if len(instances) == 0 {
		log.Println("All instances is running")

		return
	}

	waitGroup.Add(len(instances))

	for _, instance := range instances {
		instance := instance
		go func() {
			defer waitGroup.Done()
			log.Printf("Starting instance: %s", instance.GetName())

			req := &computepb.StartInstanceRequest{
				Instance: instance.GetName(),
				Project:  projectID,
				Zone:     zones[instance.GetZone()],
			}

			operation, err := instanceClient.Start(ctx, req)
			if err != nil {
				log.Printf("Error starting instance '%s': %s", instance.GetName(), err)

				return
			}

			err = operation.Wait(ctx)
			if err != nil {
				log.Printf("Error waiting start '%s': %s", instance.GetName(), err)
			}

			log.Printf("Started instance: %s", instance.GetName())
		}()
	}
}

func main() {
	projectID := os.Getenv("PROJECT_ID")
	if projectID == "" {
		log.Fatal("PROJECT_ID is empty")
	}

	ctx, cancel := context.WithCancel(context.Background())

	instancesClient, err := compute.NewInstancesRESTClient(ctx)
	if err != nil {
		log.Fatalf("Error creating instance client: %s", err)
	}
	defer instancesClient.Close()

	zones, err := getZones(projectID)
	if err != nil {
		log.Printf("Error getting zones: %s", err)

		defer os.Exit(1)

		return
	}

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGHUP, syscall.SIGTERM)
	log.Println("Waiting stop signal")

	ticker := time.NewTicker(tickerDuration)
	waitGroup := sync.WaitGroup{}

	for {
		go resumeInstances(ctx, &waitGroup, instancesClient, zones, projectID)
		select {
		case <-ticker.C:
			waitGroup.Wait()

			continue
		case <-sig:
			cancel()
			waitGroup.Wait()

			return
		}
	}
}
