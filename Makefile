# WaterScribe - Production Deployment

.PHONY: build run stop clean logs shell test

# Docker commands
build:
	docker compose build --no-cache

run:
	docker compose up -d

stop:
	docker compose down

restart:
	docker compose down && docker compose up -d

logs:
	docker compose logs -f waterscribe

shell:
	docker compose exec waterscribe /bin/bash

# Development commands  
dev:
	python3 waterscribe_prod.py

test:
	python3 -m pytest tests/ -v

# Maintenance
clean:
	docker compose down -v
	docker system prune -f
	docker volume prune -f

backup-db:
	cp aquarium.db aquarium.db.backup.$$(date +%Y%m%d_%H%M%S)

restore-db:
	@echo "Usage: make restore-db FILE=aquarium.db.backup.20260215_105500"
	@if [ -n "$(FILE)" ]; then cp $(FILE) aquarium.db; fi

# Status
status:
	@echo "=== Container Status ==="
	docker compose ps
	@echo "\n=== Health Check ==="
	curl -s http://localhost:5000/health | python3 -m json.tool || echo "Service not responding"
	@echo "\n=== Logs (last 10 lines) ==="
	docker compose logs --tail=10 waterscribe

# Initial setup
setup:
	@echo "🚀 Setting up WaterScribe production environment..."
	make build
	make run
	@echo "⏳ Waiting for service to start..."
	sleep 10
	make status
	@echo "✅ WaterScribe is running at http://localhost:5000"