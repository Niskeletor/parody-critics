# Parody Critics API — Build & Deploy
# Usage: make <target>

IMAGE      := parody-critics-api
REMOTE     := stilgar
COMPOSE    := /home/stilgar/docker/parody-critics/docker-compose.yml
VOLUME     := parody_critics_data
CONTAINER  := parody-critics-api

.PHONY: build push deploy logs shell restart db-setup help

help:
	@echo "Targets:"
	@echo "  build      Build image locally"
	@echo "  push       Transfer image to DUNE via SSH pipe"
	@echo "  deploy     build + push + restart"
	@echo "  restart    Restart container on DUNE (no rebuild)"
	@echo "  logs       Tail container logs"
	@echo "  shell      Open shell in running container"
	@echo "  db-setup   One-time: create volume + fix permissions"

build:
	docker build -t $(IMAGE):latest .

push:
	@echo "→ Transferring image to $(REMOTE)..."
	docker save $(IMAGE):latest | gzip | ssh $(REMOTE) "gunzip | docker load"
	@echo "✓ Image loaded on $(REMOTE)"

deploy: build push restart

restart:
	ssh $(REMOTE) "docker compose -f $(COMPOSE) up -d --force-recreate"
	@echo "✓ Container restarted"

logs:
	ssh $(REMOTE) "docker logs $(CONTAINER) -f --tail=100"

shell:
	ssh $(REMOTE) "docker exec -it $(CONTAINER) bash"

db-setup:
	@echo "→ Creating volume $(VOLUME) with correct permissions..."
	ssh $(REMOTE) "docker volume create $(VOLUME) && \
	  docker run --rm -v $(VOLUME):/data alpine sh -c 'chown 1000:1000 /data && chmod 755 /data'"
	@echo "✓ Volume ready — now copy your DB if needed:"
	@echo "  docker run --rm -v $(VOLUME):/data -v \$$(pwd):/src alpine cp /src/database/critics.db /data/"
	@echo "  docker run --rm -v $(VOLUME):/data alpine chown 1000:1000 /data/critics.db"
