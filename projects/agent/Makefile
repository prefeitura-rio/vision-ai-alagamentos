image_name = $(or $(IMAGE_NAME),ghcr.io/prefeitura-rio/vision-ai-agent)
image_tag = $(or $(IMAGE_TAG),latest)

.PHONY: docker-build
docker-build:
	cp -p -r ../../libs libs
	docker build . -t $(image_name):$(image_tag)

.PHONY: docker-publish
docker-publish:
	docker push $(image_name):$(image_tag)

.PHONY: docker
docker: docker-build docker-publish

.PHONY: clean
clean:
	rm -rf libs
