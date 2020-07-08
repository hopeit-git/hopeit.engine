#!/usr/bin/env bash
echo "Starting hopeit.engine on Docker"
cd ../docker
docker-compose up -d
echo ======== Running on http://localhost:8025 ========

