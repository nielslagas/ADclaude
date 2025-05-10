#!/bin/bash
# Script to run the report cleanup utility within the Docker container

echo "Starting report cleanup process..."

# Enter the backend container and run the script
docker compose exec backend-api python /app/clean_existing_reports.py

echo "Cleanup process completed."