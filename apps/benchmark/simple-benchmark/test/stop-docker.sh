#!/usr/bin/env bash
echo "Stopping hopeit-engine Docker"
cd ../docker
docker-compose down
echo "Done"
