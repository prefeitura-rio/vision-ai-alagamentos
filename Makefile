agent_image_name = vision-ai-agent
agent_image_tag = compose

.PHONY: docker-build
docker-build:
	export IMAGE_NAME=$(agent_image_name) IMAGE_TAG=$(agent_image_tag) && cd ./projects/agent && make docker-build

.PHONY: docker
docker: docker-build

.PHONY: agent-up
agent-up: docker-build
	docker compose up -d --build agent

.PHONY:
compose-down:
	docker compose down

.PHONY: clean
clean: compose-down
	docker compose down -v
	cd ./projects/agent && make clean

