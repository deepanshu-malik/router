# OSRM Bike Router for India

A Docker-based OSRM routing engine with bicycle profile optimization for India and its regions.

---

## Features

- Pre-configured bicycle routing profiles
- Support for all Indian regions
- Automatic data processing pipeline
- Easy-to-use setup script

---

## Quick Start

### Prerequisites

- **Docker** installed and running
- **2GB+ disk space** (depending on the region)
- **4GB+ RAM** recommended

---

### Installation

1. **Make the setup script executable**:
   ```bash
   chmod +x setup_router.sh
   ```

2. **Run the setup script**:
   ```bash
   ./setup_router.sh
   ```

---

## Available Regions

| Region              | Size   | Download Command                                                                 |
|---------------------|--------|----------------------------------------------------------------------------------|
| Complete India      | 1.5 GB | `wget https://download.geofabrik.de/asia/india-latest.osm.pbf`                   |
| Northern Zone       | 201 MB | `wget https://download.geofabrik.de/asia/india/northern-zone-latest.osm.pbf`     |
| Central Zone        | 324 MB | `wget https://download.geofabrik.de/asia/india/central-zone-latest.osm.pbf`      |
| Eastern Zone        | 221 MB | `wget https://download.geofabrik.de/asia/india/eastern-zone-latest.osm.pbf`      |
| North-Eastern Zone  | 86 MB  | `wget https://download.geofabrik.de/asia/india/north-eastern-zone-latest.osm.pbf`|
| Southern Zone       | 498 MB | `wget https://download.geofabrik.de/asia/india/southern-zone-latest.osm.pbf`     |
| Western Zone        | 184 MB | `wget https://download.geofabrik.de/asia/india/western-zone-latest.osm.pbf`      |

**All data was last updated:** `2025-03-30T20:21:01Z`

---

## Manual Setup

### 1. Download OSM Data
Choose your preferred region from the table above.

### 2. Process Data
Run the following commands to process the data:

```bash
# Extract with bicycle profile
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend \
    osrm-extract -p /opt/bicycle.lua /data/REGION_NAME-latest.osm.pbf

# Partition the data
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend \
    osrm-partition /data/REGION_NAME-latest

# Customize the data
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend \
    osrm-customize /data/REGION_NAME-latest
```

### 3. Start Routing Server
```bash
docker run -t -i -p 5000:5000 -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend \
    osrm-routed --algorithm mld /data/REGION_NAME-latest
```

---

## Usage

Once the server is running, access the routing engine at:

```
http://localhost:5000/route/v1/bike/START_LON,START_LAT;END_LON,END_LAT
```

### Example
Routing from Connaught Place to India Gate:
```
http://localhost:5000/route/v1/bike/77.2183,28.6315;77.2298,28.6129
```

---

## Customization

### Delhi-Specific Optimizations
The system includes special handling for:

- Monsoon waterlogging areas
- High-theft risk zones
- Poor road surfaces
- Bike lane prioritization

To modify these settings, edit the `delhi-bicycle.lua` profile.

---

## Maintenance

### Update Data
To update your OSM data:

1. Delete the old `.osm.pbf` file.
2. Re-run the download command.
3. Repeat the processing steps.

### Automatic Updates
Set up a cron job to check for updates weekly:
```bash
0 3 * * 1 cd /path/to/router && ./setup_router.sh
```

---

## Troubleshooting

### Common Issues

1. **No edges remaining error**:
   - Verify your OSM data contains highway tags.
   - Try a smaller region first.

2. **Docker permissions**:
   ```bash
   sudo usermod -aG docker $USER
   ```

3. **Server not responding**:
   - Check if port `5000` is in use.
   - Verify the Docker container is running.

---