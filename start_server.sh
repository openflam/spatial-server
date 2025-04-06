#!/bin/sh

# Check if the HTTPS environment variable is set to true
if [ "$HTTPS" = "true" ]; then
    echo "Starting Flask server in HTTPS mode..."
    flask --app spatial_server/server run --host 0.0.0.0 --port 8001 --cert=/ssl/cert.pem --key=/ssl/key.pem
else
    echo "Starting Flask server in HTTP mode..."
    flask --app spatial_server/server run --host 0.0.0.0 --port 8001
fi