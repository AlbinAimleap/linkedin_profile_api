IMAGE_NAME=linkedin
BUILD_NAME=latest

.PHONY: build
build:
	docker build -t $(IMAGE_NAME):$(BUILD_NAME) .

.PHONY: run
run:
	docker run -it -p 8000:8000 $(IMAGE_NAME):$(BUILD_NAME)

.PHONY: build-run
dbuild: build run

.PHONY: stop
stop:
	docker stop $(docker ps -q --filter ancestor=$(IMAGE_NAME):$(BUILD_NAME))

.PHONY: clean
clean:
	docker system prune -f