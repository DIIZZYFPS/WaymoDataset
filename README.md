# 🚗 Waymo Edge Case Analysis System

An intelligent system for detecting, classifying, and analyzing edge cases in autonomous driving data from the Waymo Open Dataset. Features an interactive React dashboard and AI-powered analysis using Google Gemini.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Usage](#usage)
- [Database Schema](#database-schema)
- [API Documentation](#api-documentation)
- [AI Agent Capabilities](#ai-agent-capabilities)
- [Configuration](#configuration)
- [Performance Metrics](#performance-metrics)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

This project processes the Waymo End-to-End (E2E) driving dataset to automatically detect and classify edge case scenarios such as:
- **Hard braking events** (-0.8 m/s² threshold - emergency braking level)
- **Evasive maneuvers** (0.6 m/s² lateral acceleration - sharp turns)
- **High jerk events** (0.4 m/s³ - sudden acceleration changes)

The system combines **industry-standard safety thresholds** with **AI-powered analysis** using Google Gemini for both SQL query generation and computer vision analysis of driving scenarios.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Frontend (React + TypeScript)              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │  Dashboard       │  │  AI Chat        │  │  Charts      ││
│  │  - KPI Cards     │  │  - SQL Queries  │  │  - Scatter   ││
│  │  - Filters       │  │  - Vision AI    │  │  - Histogram ││
│  │  - Pre-flagged   │  │  - Markdown     │  │  - Box Plot  ││
│  └─────────────────┘  └─────────────────┘  └──────────────┘│
│            │ TanStack Query (Data Fetching)                  │
└────────────┼───────────────────────────────────────────────┘
             │ HTTP/REST
             ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI + Python)                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │  REST API        │  │  Gemini Agent   │  │  SQLite DB   ││
│  │  - Stats         │  │  - SQL Tool     │  │  - Frames    ││
│  │  - Charts        │  │  - Vision Tool  │  │  - Edge Cases││
│  │  - Tables        │  │  - Custom Funcs │  │  - Thumbnails││
│  └─────────────────┘  └─────────────────┘  └──────────────┘│
└─────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│              Data Processing (Docker Container)              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │  TensorFlow      │  │  Motion Analysis│  │  Image Proc  ││
│  │  - Proto Parsing │  │  - Accel/Jerk   │  │  - Panorama  ││
│  │  - TFRecord I/O  │  │  - Severity Calc│  │  - Thumbnail ││
│  └─────────────────┘  └─────────────────┘  └──────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Technology Stack:**
- **Frontend:** React 19, TypeScript, Vite, TanStack Query, Recharts, Radix UI, Tailwind CSS
- **Backend:** Python 3.11, FastAPI, SQLite, Google ADK (Gemini 2.0/2.5)
- **Processing:** TensorFlow, OpenCV, NumPy, Pandas, Docker

## ✨ Features

### Data Processing
- ✅ **Automated Edge Case Detection** - Industry-standard thresholds
- ✅ **Motion Analysis** - Speed, acceleration, jerk calculation from velocity data
- ✅ **Normalized Severity Scoring** - 0.0-1.0 scale (3x threshold = 1.0)
- ✅ **Panorama Generation** - 3-camera front view stitching (LEFT/CENTER/RIGHT)
- ✅ **Batch Processing** - Docker containerized pipeline with automated cleanup
- ✅ **Persistent Storage** - SQLite with WAL mode for concurrent access

### Backend API
- ✅ **RESTful Endpoints** - Dashboard stats, charts, tables with filtering
- ✅ **AI Agent Integration** - Google Gemini 2.5 Flash orchestration
- ✅ **Custom SQL Functions** - STDEV, VARIANCE, MEDIAN aggregates
- ✅ **Vision Analysis** - Gemini 2.0 Flash Exp for image understanding
- ✅ **Security** - SQL validation, blocks SELECT *, panorama access control

### Frontend Dashboard
- ✅ **Interactive Visualizations** - Scatter, histogram, box plot, pie charts
- ✅ **Real-time Filtering** - Type, file, severity range with 150ms debouncing
- ✅ **Performance Optimization** - Client-side sampling (max 2,000 points)
- ✅ **AI Chat Interface** - Floating drawer with Markdown rendering
- ✅ **Responsive Design** - Tailwind CSS + shadcn/ui components
- ✅ **Image Viewer** - Thumbnail modal with panorama display

## 📁 Project Structure

```
WaymoDataset/
├── load_dataset.py              # Data processing script (TensorFlow + OpenCV)
├── process_waymo.sh             # Automated batch processing pipeline
├── dashboard.py                 # Legacy Dash dashboard
├── explore_proto.py             # Proto structure exploration
├── query_motion_data.py         # Motion data queries
├── Dockerfile                   # Container for data processing
├── docker-compose.yml           # Docker Compose setup
├── README.md                    # This file
│
├── waymo-api/                   # FastAPI Backend
│   ├── main.py                  # REST API endpoints (670 lines)
│   ├── requirements.txt         # Python dependencies
│   ├── .env                     # Environment variables (GOOGLE_API_KEY)
│   └── Waymo_Agent/
│       ├── agent.py             # Gemini AI agent with SQL + Vision tools
│       └── __init__.py
│
├── Waymo-Dash/                  # React Frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Index.tsx        # Main dashboard page
│   │   │   └── NotFound.tsx
│   │   ├── components/
│   │   │   └── dashboard/
│   │   │       ├── ChatSidebar.tsx      # AI chat interface
│   │   │       ├── Charts.tsx           # Data visualizations
│   │   │       ├── FilterControls.tsx   # Filter UI
│   │   │       ├── KPICards.tsx         # Summary stats
│   │   │       ├── PreFlaggedTable.tsx  # Edge case table
│   │   │       ├── ThumbnailModal.tsx   # Image viewer
│   │   │       └── AdHocQuery.tsx       # Custom queries
│   │   └── hooks/
│   │       ├── useEdgeCaseData.ts       # Data fetching hook
│   │       └── useAgentChat.ts          # AI chat hook
│   ├── package.json             # Node dependencies
│   ├── vite.config.ts           # Vite configuration
│   └── tsconfig.json            # TypeScript configuration
│
└── waymo_dataset/
    ├── downloads/               # Downloaded TFRecord files (auto-cleanup)
    ├── training/                # Training dataset files
    └── results/
        ├── edge_cases.db        # SQLite database (WAL mode)
        └── thresholds.json      # Detection thresholds (industry standard)
```

## 🔧 Prerequisites

### Backend Requirements
- Python 3.11+
- Google AI API Key (for Gemini models)
- SQLite3

### Frontend Requirements
- Node.js 18+
- npm or yarn

### Data Processing (Optional)
- Docker & Docker Compose (for containerized processing)
- Google Cloud SDK (gsutil) - for downloading from Waymo GCS bucket
- ~50GB free disk space (for batch processing)

## 📦 Setup Instructions

### 1️⃣ Backend Setup (FastAPI)

```bash
# Navigate to backend directory
cd waymo-api

# Install dependencies
pip install -r requirements.txt

# Create .env file with your Google AI API key
echo "GOOGLE_API_KEY=your_api_key_here" > .env

# Start the FastAPI server (runs on http://localhost:8000)
python main.py
```

**Backend Dependencies:**
```
fastapi
uvicorn
pandas
numpy
google-adk
python-dotenv
opencv-python
Pillow
```

### 2️⃣ Frontend Setup (React)

```bash
# Navigate to frontend directory
cd Waymo-Dash

# Install dependencies
npm install

# Start the development server (runs on http://localhost:5173)
npm run dev
```

**Frontend Dependencies:**
- React 19 with TypeScript
- TanStack Query (data fetching)
- Recharts (visualizations)
- Radix UI (components)
- Tailwind CSS (styling)
- Vaul (drawer component)

### 3️⃣ Data Processing Setup (Docker)

```bash
# Build the Docker container
docker-compose build

# Process a single TFRecord file
docker-compose run --rm waymo-e2e-loader python load_dataset.py /waymo_dataset/downloads/your_file.tfrecord

# Or use the automated batch processing script
bash process_waymo.sh
```

**process_waymo.sh Features:**
- Downloads 5 files from Waymo GCS bucket
- Processes each file sequentially
- Auto-deletes tfrecord after processing (saves disk space)
- Preserves database and results

## 🚀 Usage

### Starting the System

1. **Start Backend:**
```bash
cd waymo-api
python main.py
# API available at http://localhost:8000
```

2. **Start Frontend:**
```bash
cd Waymo-Dash
npm run dev
# Dashboard available at http://localhost:5173
```

3. **Access Dashboard:**
- Open browser to `http://localhost:5173`
- Use filters to explore edge cases
- Click chat icon to interact with AI agent

### Processing Waymo Data

#### Option 1: Single File Processing
```bash
# Download a file
gsutil cp gs://waymo_open_dataset_e2ed/2025.01.15_E2ED_Training_Release/tfrecords/file.tfrecord ./waymo_dataset/downloads/

# Process with Docker
docker-compose run --rm waymo-e2e-loader python load_dataset.py /waymo_dataset/downloads/file.tfrecord

# Cleanup
rm ./waymo_dataset/downloads/file.tfrecord
```

#### Option 2: Batch Processing (5 files)
```bash
bash process_waymo.sh
```

### Using the AI Agent

The AI agent can answer questions about the dataset using SQL queries and vision analysis:

**Example Queries:**

1. **SQL-based queries:**
```
"How many hard braking events occurred?"
"Show me the top 5 most severe edge cases"
"What's the average severity for evasive maneuvers?"
"Which file has the most edge cases?"
"What's the standard deviation of severity scores?"
```

2. **Vision analysis queries:**
```
"What caused the edge case in frame 51?"
"Analyze the driving scenario in frame 123"
"Show me what happened during frame 87 with hard braking"
```

3. **Combined queries:**
```
"Find frames with hard braking while turning left and analyze them"
"What's common among the most severe edge cases?"
```

## 🗄️ Database Schema

### Simplified Schema (Current)

The database uses a **simplified foreign key design** for efficient JOINs:

```sql
-- Frames table (primary data)
CREATE TABLE frames (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Global unique key
    frame_id INTEGER NOT NULL,              -- Per-file counter (NOT unique across files!)
    file_name TEXT NOT NULL,
    timestamp BIGINT,
    intent TEXT,                            -- "go_straight", "turn_left", "turn_right", etc.
    speed_min REAL,
    speed_max REAL,
    speed_mean REAL,
    accel_x_min REAL,                       -- Longitudinal acceleration (braking/acceleration)
    accel_x_max REAL,
    accel_y_min REAL,                       -- Lateral acceleration (turning)
    accel_y_max REAL,
    jerk_x_max REAL,                        -- Longitudinal jerk (smoothness)
    jerk_y_max REAL,                        -- Lateral jerk
    panorama_thumbnail BLOB,                -- 3-camera front view JPEG (512px width)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Edge cases table (detected anomalies)
CREATE TABLE edge_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_table_id INTEGER NOT NULL,        -- Foreign key to frames.id
    edge_case_type TEXT NOT NULL,           -- "hard_brake", "evasive_maneuver", "high_jerk"
    severity REAL NOT NULL,                 -- 0.0-1.0 normalized (3x threshold = 1.0)
    reason TEXT,                            -- Human-readable explanation
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(frame_table_id) REFERENCES frames(id)
);

-- Indexes for performance
CREATE INDEX idx_frames_file ON frames(file_name);
CREATE INDEX idx_edge_cases_frame ON edge_cases(frame_table_id);
CREATE INDEX idx_edge_cases_type ON edge_cases(edge_case_type);
```

**Key Design Decisions:**

1. **Simple Foreign Key:** Use `frames.id` (auto-increment) instead of composite key (frame_id + file_name)
   - ✅ Eliminates JOIN duplicates
   - ✅ Faster queries
   - ✅ Simpler agent SQL generation

2. **Normalized Severity:** 0.0-1.0 scale instead of raw acceleration values
   - 0.0 = at threshold (barely an edge case)
   - 0.5 = 2x threshold (moderate severity)
   - 1.0 = 3x threshold (extremely severe)

3. **Embedded Thumbnails:** BLOB storage for panorama images
   - ✅ No external file dependencies
   - ✅ Faster vision analysis
   - ✅ Simplified deployment

## 📡 API Documentation

### Base URL: `http://localhost:8000`

### Dashboard Endpoints

#### `GET /api/dashboard/summary`
Returns dashboard summary statistics.

**Response:**
```json
{
  "totalEdgeCases": 115,
  "filesProcessed": 5,
  "edgeCaseTypes": ["hard_brake", "evasive_maneuver", "high_jerk"],
  "filesWithEdgeCases": ["file1.tfrecord", "file2.tfrecord", ...],
  "edgeCaseTypeCounts": {
    "hard_brake": 35,
    "evasive_maneuver": 20,
    "high_jerk": 60
  }
}
```

#### `GET /api/dashboard/filters`
Returns available filter options.

**Response:**
```json
{
  "types": ["hard_brake", "evasive_maneuver", "high_jerk"],
  "files": ["file1.tfrecord", "file2.tfrecord", ...]
}
```

### Chart Endpoints

#### `GET /api/charts/scatter`
Returns scatter plot data (speed vs acceleration).

**Query Parameters:**
- `type` (optional): Filter by edge case type
- `file` (optional): Filter by file name
- `severity_min` (optional): Minimum severity
- `severity_max` (optional): Maximum severity

**Response:**
```json
{
  "data": [
    {
      "speed": 15.2,
      "accel": -0.92,
      "severity": 0.15,
      "edge_case_type": "hard_brake",
      "file_name": "file1.tfrecord"
    },
    ...
  ]
}
```

#### `GET /api/charts/histogram`
Returns severity distribution histogram.

**Response:**
```json
{
  "data": [
    {"severity_range": "0.0-0.1", "count": 25},
    {"severity_range": "0.1-0.2", "count": 35},
    ...
  ]
}
```

#### `GET /api/charts/box`
Returns box plot data for motion metrics.

**Response:**
```json
{
  "data": [
    {
      "metric": "speed_max",
      "min": 0.0,
      "q1": 5.2,
      "median": 12.5,
      "q3": 18.9,
      "max": 29.78
    },
    ...
  ]
}
```

#### `GET /api/charts/pie`
Returns pie chart data for edge case type distribution.

**Response:**
```json
{
  "data": [
    {"name": "hard_brake", "value": 35},
    {"name": "evasive_maneuver", "value": 20},
    {"name": "high_jerk", "value": 60}
  ]
}
```

### Table Endpoints

#### `GET /api/table/preflagged`
Returns paginated pre-flagged edge cases.

**Query Parameters:**
- `page` (default: 1): Page number
- `limit` (default: 25): Items per page
- `type` (optional): Filter by edge case type
- `file` (optional): Filter by file name
- `severity_min` (optional): Minimum severity
- `severity_max` (optional): Maximum severity

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "frame_id": 51,
      "file_name": "file1.tfrecord",
      "edge_case_type": "hard_brake",
      "severity": 0.65,
      "intent": "go_straight",
      "speed_max": 18.5,
      "accel_x_min": -1.15,
      "panorama_base64": "data:image/jpeg;base64,/9j/4AAQ..."
    },
    ...
  ],
  "total": 115,
  "page": 1,
  "pages": 5
}
```

### AI Agent Endpoints

#### `POST /api/agent/chat`
Send a message to the AI agent for SQL queries or vision analysis.

**Request:**
```json
{
  "message": "How many hard braking events occurred?",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "response": "According to the database, there are 35 hard braking events detected across all files..."
}
```

## 🤖 AI Agent Capabilities

The AI agent uses **Google ADK framework** with two specialized tools:

### 1. SQL Query Tool (`execute_sql_query`)

**Features:**
- Executes SELECT queries on the database
- Custom aggregate functions: STDEV, VARIANCE, MEDIAN
- Automatic SQL validation (blocks SELECT *, panorama_thumbnail)
- Returns JSON formatted results

**Custom Aggregate Functions:**
```sql
-- Standard deviation (sample)
SELECT edge_case_type, STDEV(severity) as severity_std
FROM edge_cases
GROUP BY edge_case_type;

-- Median severity
SELECT edge_case_type, MEDIAN(severity) as median_severity
FROM edge_cases
GROUP BY edge_case_type;

-- Variance
SELECT VARIANCE(severity) as severity_variance FROM edge_cases;
```

**Example Agent SQL Generation:**
```
User: "Show high severity hard brakes"

Agent generates:
SELECT f.frame_id, f.file_name, ec.severity, f.speed_max, f.accel_x_min
FROM frames f
JOIN edge_cases ec ON f.id = ec.frame_table_id
WHERE ec.edge_case_type = 'hard_brake' AND ec.severity > 0.8
ORDER BY ec.severity DESC;
```

### 2. Vision Analysis Tool (`classify_image`)

**Features:**
- Retrieves panorama thumbnail from database
- Converts BLOB to base64 for Gemini Vision API
- Provides motion context (speed, acceleration, jerk, intent)
- Uses Gemini 2.0 Flash Exp for image understanding

**Example Vision Analysis:**
```
User: "What caused the edge case in frame 51?"

Agent:
1. Queries database for frame 51 data
2. Retrieves panorama_thumbnail BLOB
3. Sends to Gemini Vision with context:
   - Intent: "go_straight"
   - Speed: 18.5 m/s
   - Accel: -1.15 m/s²
   - Edge case: "hard_brake", severity 0.65

Response:
"VISION ANALYSIS: The panorama shows a vehicle ahead suddenly
braking, causing the ego vehicle to perform emergency braking.
The road is clear with good visibility.

MOTION DATA: Speed was 18.5 m/s when hard braking (-1.15 m/s²)
was detected. This is 44% beyond the -0.8 threshold, indicating
moderate severity (0.65/1.0)."
```

### Agent System Instruction

The agent is configured with comprehensive schema documentation:

```python
root_agent = Agent(
    model='gemini-2.5-flash',
    instruction="""Expert Waymo Data Analyst with SQL + vision capabilities.

DATABASE SCHEMA:
- frames.id (PK) - Global unique key for JOINs
- frames.frame_id - Per-file counter (NOT unique across files!)
- edge_cases.frame_table_id (FK) - References frames.id

CRITICAL SQL RULES:
1. JOIN KEY: Always use frames.id = edge_cases.frame_table_id
2. NEVER SELECT panorama_thumbnail (use classify_image tool instead)
3. NEVER use SELECT * FROM frames (too much data)
4. Supported functions: COUNT, AVG, STDEV, VARIANCE, MEDIAN, GROUP_CONCAT

EXAMPLES:
- "Show high severity": 
  SELECT f.frame_id, ec.severity FROM frames f 
  JOIN edge_cases ec ON f.id = ec.frame_table_id 
  WHERE ec.severity > 0.8

- "Analyze frame 123": classify_image(123)

- "Hard brakes while turning":
  SELECT f.frame_id, f.intent FROM frames f
  JOIN edge_cases ec ON f.id = ec.frame_table_id
  WHERE ec.edge_case_type = 'hard_brake' 
  AND f.intent LIKE '%turn%'
""",
    tools=[execute_sql_query, classify_image]
)
```

## ⚙️ Configuration

### Thresholds (Industry Standard)

Located in `waymo_dataset/results/thresholds.json`:

```json
{
  "hard_brake": -0.8,
  "lateral": 0.6,
  "jerk": 0.4
}
```

**Threshold Definitions:**

| Threshold | Value | Description |
|-----------|-------|-------------|
| `hard_brake` | -0.8 m/s² | Emergency braking level (negative = deceleration) |
| `lateral` | 0.6 m/s² | Evasive maneuver threshold (sharp turns) |
| `jerk` | 0.4 m/s³ | Abrupt pedal input (sudden acceleration change) |

**Severity Calculation:**

```python
# Normalized severity: 0.0 at threshold, 1.0 at 3x threshold
def calculate_normalized_severity(raw_value, threshold, is_negative=False):
    if is_negative:
        # For hard braking (negative acceleration)
        raw_abs = abs(raw_value)
        threshold_abs = abs(threshold)
        max_expected = threshold_abs * 3
        severity = (raw_abs - threshold_abs) / (max_expected - threshold_abs)
    else:
        # For lateral/jerk (positive values)
        max_expected = threshold * 3
        severity = (raw_value - threshold) / (max_expected - threshold)
    
    return max(0.0, min(severity, 1.0))  # Clamp to [0, 1]
```

**Examples:**
- `accel_x_min = -0.8` → severity = 0.0 (at threshold)
- `accel_x_min = -1.6` → severity = 0.5 (2x threshold)
- `accel_x_min = -2.4` → severity = 1.0 (3x threshold)

### Environment Variables

Create `waymo-api/.env`:
```bash
GOOGLE_API_KEY=your_google_ai_api_key_here
```

Get your API key from: https://aistudio.google.com/app/apikey

## 📊 Performance Metrics

### Dataset Processing Results (5 Files)

**Overall Statistics:**
- **Total Frames:** 3,819
- **Edge Cases Detected:** 115 (3.0% detection rate)
- **Files Processed:** 5 tfrecord files
- **Processing Time:** ~2-3 minutes per file (Docker)

**Edge Case Distribution:**
| Type | Count | Percentage |
|------|-------|------------|
| High Jerk | 60 | 52.2% |
| Hard Brake | 35 | 30.4% |
| Evasive Maneuver | 20 | 17.4% |

**Severity Statistics:**
- **Minimum:** 0.0007 (barely above threshold)
- **Maximum:** 0.9987 (near 3x threshold)
- **Average:** 0.1785 (moderate severity)
- **Standard Deviation:** 0.215

**Motion Extremes:**
- **Max Speed:** 29.78 m/s (~66 mph)
- **Min Acceleration (braking):** -1.72 m/s²
- **Max Lateral Acceleration:** 0.92 m/s²
- **Max Jerk:** 1.20 m/s³

### Performance Optimizations

**Backend:**
- ✅ SQLite WAL mode for concurrent reads
- ✅ Indexed foreign keys (frame_table_id)
- ✅ Simplified JOINs (no CTE aggregation needed)
- ✅ Pandas for efficient data transformations

**Frontend:**
- ✅ Client-side data sampling (max 2,000 scatter points)
- ✅ Debounced severity slider (150ms delay)
- ✅ TanStack Query caching (5-minute stale time)
- ✅ Lazy loading for thumbnails (base64 on-demand)

**Data Processing:**
- ✅ Docker containerization (isolated environment)
- ✅ Auto-cleanup of tfrecord files (saves ~10GB per file)
- ✅ Batch processing pipeline (5 files sequentially)
- ✅ JPEG thumbnail compression (512px width, 75% quality)

## 🐛 Troubleshooting

### Common Issues

#### 1. Backend won't start - Missing GOOGLE_API_KEY

**Error:**
```
ValueError: GOOGLE_API_KEY environment variable not found
```

**Solution:**
```bash
cd waymo-api
echo "GOOGLE_API_KEY=your_key_here" > .env
```

#### 2. Frontend can't connect to backend

**Error:**
```
Failed to fetch: http://localhost:8000/api/dashboard/summary
```

**Solution:**
- Ensure backend is running: `cd waymo-api && python main.py`
- Check backend is on port 8000: `netstat -an | findstr 8000` (Windows)
- Verify no CORS issues in browser console

#### 3. Database locked error

**Error:**
```
sqlite3.OperationalError: database is locked
```

**Solution:**
- Enable WAL mode (already configured):
  ```python
  cursor.execute("PRAGMA journal_mode=WAL")
  ```
- Close all database connections properly
- Restart backend if issue persists

#### 4. Agent SQL queries return empty results

**Possible Causes:**
- Using `frame_id` without `file_name` (frame_id not unique across files!)
- Missing JOIN on `frames.id = edge_cases.frame_table_id`

**Solution:**
- Always JOIN using `frames.id` as the foreign key
- Refer to agent system instruction for correct JOIN syntax

#### 5. Vision analysis fails

**Error:**
```
ValueError: Cannot select 'panorama_thumbnail'. Use classify_image() instead
```

**Solution:**
- Don't query panorama_thumbnail directly via SQL
- Use agent's classify_image tool: `"Analyze frame 51"`

#### 6. Docker processing fails

**Error:**
```
Cannot connect to the Docker daemon
```

**Solution:**
```bash
# Windows: Start Docker Desktop
# Linux: sudo systemctl start docker

# Rebuild container if needed
docker-compose build --no-cache
```

### Performance Issues

#### Scatter chart too slow with many points

**Solution:** Already optimized with client-side sampling (max 2,000 points)

#### Severity slider lagging

**Solution:** Already optimized with 150ms debounce

#### Agent responses slow

**Optimization Tips:**
- Use specific queries instead of `SELECT *`
- Limit results with `LIMIT` clause
- Vision analysis takes 2-5 seconds (Gemini API call)

### Data Quality Issues

#### Low detection rate (< 1%)

**Check:**
- Thresholds too strict? (default: -0.8, 0.6, 0.4)
- Motion data valid? (check velocity array length > 0)

#### Severity scores > 1.0

**This should never happen** - severity is clamped to [0, 1]
- Check `calculate_normalized_severity` function

## 📝 Development Notes

### Adding New Edge Case Types

1. **Update thresholds.json:**
```json
{
  "hard_brake": -0.8,
  "lateral": 0.6,
  "jerk": 0.4,
  "low_speed_stop": 2.0
}
```

2. **Add detection logic in load_dataset.py:**
```python
# Detect low speed stop
if speed_mean < THRESHOLDS['low_speed_stop']:
    severity = calculate_normalized_severity(...)
    store_edge_case(db_conn, frame_table_id, 'low_speed_stop', severity, reason)
```

3. **Update frontend filters** in FilterControls.tsx

### Database Migrations

**To reset database:**
```bash
# Backup first!
cp waymo_dataset/results/edge_cases.db waymo_dataset/results/edge_cases_backup.db

# Delete database
rm waymo_dataset/results/edge_cases.db

# Reprocess data
bash process_waymo.sh
```

### Testing Agent Queries

```bash
# Test backend directly
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many edge cases?"}'
```

## 📚 Resources

- [Waymo Open Dataset](https://waymo.com/open/)
- [Google ADK Documentation](https://github.com/googleapis/python-genai)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Recharts Documentation](https://recharts.org/)

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please open an issue or PR.

## 📧 Contact

For questions or issues, please open a GitHub issue.

---

**Built with ❤️ for autonomous vehicle safety research**
