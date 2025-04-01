#!/bin/bash

# router setup script
set -e

echo "Setting up OSRM router for India regions"

# Step 1: Download OSM data
echo "Step 1: Downloading OSM data"
echo "Choose region:"
echo "1) India (1.5GB)"
echo "2) Northern Zone (201MB)"
echo "3) Central Zone (324MB)"
echo "4) Eastern Zone (221MB)"
echo "5) North-Eastern Zone (86MB)"
echo "6) Southern Zone (498MB)"
echo "7) Western Zone (184MB)"
read -p "Enter choice (1-7): " choice

case $choice in
    1)
        FILE="india-latest.osm.pbf"
        URL="https://download.geofabrik.de/asia/india-latest.osm.pbf"
        ;;
    2)
        FILE="northern-zone-latest.osm.pbf"
        URL="https://download.geofabrik.de/asia/india/northern-zone-latest.osm.pbf"
        ;;
    3)
        FILE="central-zone-latest.osm.pbf"
        URL="https://download.geofabrik.de/asia/india/central-zone-latest.osm.pbf"
        ;;
    4)
        FILE="eastern-zone-latest.osm.pbf"
        URL="https://download.geofabrik.de/asia/india/eastern-zone-latest.osm.pbf"
        ;;
    5)
        FILE="north-eastern-zone-latest.osm.pbf"
        URL="https://download.geofabrik.de/asia/india/north-eastern-zone-latest.osm.pbf"
        ;;
    6)
        FILE="southern-zone-latest.osm.pbf"
        URL="https://download.geofabrik.de/asia/india/southern-zone-latest.osm.pbf"
        ;;
    7)
        FILE="western-zone-latest.osm.pbf"
        URL="https://download.geofabrik.de/asia/india/western-zone-latest.osm.pbf"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

if [ ! -f "$FILE" ]; then
    echo "Downloading $FILE..."
    wget "$URL"
else
    echo "$FILE already exists, skipping download"
fi

# Step 2: Process data
echo -e "\nStep 2: Processing OSM data with bicycle profile"
BASE_NAME="${FILE%.osm.pbf}"

echo "Running osrm-extract..."
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend \
    osrm-extract -p /opt/bicycle.lua "/data/$FILE" || { echo "osrm-extract failed"; exit 1; }

echo "Running osrm-partition..."
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend \
    osrm-partition "/data/$BASE_NAME" || { echo "osrm-partition failed"; exit 1; }

echo "Running osrm-customize..."
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend \
    osrm-customize "/data/$BASE_NAME" || { echo "osrm-customize failed"; exit 1; }

# Step 3: Start server
echo -e "\nStep 3: Starting OSRM routing engine"
echo "Server will run on port 5000"
echo "Press Ctrl+C to stop the server"
docker run -t -i -p 5000:5000 -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend \
    osrm-routed --algorithm mld "/data/$BASE_NAME"
