#!/bin/bash

# Script om de embedding functionaliteit in de Docker-container te testen

echo "==== Test Gemini Embedding API via Docker container ===="

# Kopieer test script naar de container
docker cp test_embedding.py ai-arbeidsdeskundige_claude-backend-api-1:/app/

# Voer het script uit in de Docker-container
echo "Test script uitvoeren in backend-api container..."
docker exec ai-arbeidsdeskundige_claude-backend-api-1 python /app/test_embedding.py

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "Test succesvol afgerond!"
else
    echo "Test gefaald met exit code $exit_code"
fi

exit $exit_code