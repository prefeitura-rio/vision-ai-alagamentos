package main

import (
	"context"
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

func getZones(projectID string) (map[string]string, error) {
	ctx := context.Background()
	c, err := compute.NewZonesRESTClient(ctx)
	if err != nil {
		return nil, fmt.Errorf("error creating zone client: %s", err)
	}
	defer c.Close()

	zones := map[string]string{}

	req := &computepb.ListZonesRequest{
		Project: projectID,
	}
	it := c.List(ctx, req)
	for {
		resp, err := it.Next()
		if err == iterator.Done {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("error getting zone: %s", err)
		}
		zones[resp.GetSelfLink()] = resp.GetName()
	}

	return zones, nil
}

func resumeInstances(
	ctx context.Context,
	wg *sync.WaitGroup,
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
		if err == iterator.Done {
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

	wg.Add(len(instances))

	for _, instance := range instances {
		instance := instance
		go func() {
			defer wg.Done()
			log.Printf("Starting instance: %s", instance.GetName())

			req := &computepb.StartInstanceRequest{
				Instance: instance.GetName(),
				Project:  projectID,
				Zone:     zones[instance.GetZone()],
			}
			op, err := instanceClient.Start(ctx, req)
			if err != nil {
				log.Printf("Error starting instance '%s': %s", instance.GetName(), err)
				return
			}

			err = op.Wait(ctx)
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
		log.Fatalf("Error getting zones: %s", err)
	}

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGHUP, syscall.SIGTERM)
	log.Println("Waiting stop signal")

	ticker := time.NewTicker(10 * time.Second)
	wg := sync.WaitGroup{}
	for {
		go resumeInstances(ctx, &wg, instancesClient, zones, projectID)
		select {
		case <-ticker.C:
			wg.Wait()
			continue
		case <-sig:
			cancel()
			wg.Wait()
			return
		}
	}
}
