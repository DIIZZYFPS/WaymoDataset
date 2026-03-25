import fastapi
import sqlite3
import numpy as np
import pandas as pd
import base64
import json
import asyncio
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pathlib import Path
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    # Start background sink task
    asyncio.create_task(sink_redis_to_db())
    yield

app = fastapi.FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================== Data Backend Configuration ==================#
# Cloud-Native: BigQuery (primary storage) + GCS (image storage)

# BigQuery config
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "waymo-dataset-analysis")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "waymo_analytics")
GCS_IMAGE_BUCKET = os.getenv("GCS_IMAGE_BUCKET", "e2e-processed-images")

# Redis config (for live edge case stream from C++ engine)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Try to initialize BigQuery client
try:
    from google.cloud import bigquery
    bq_client = bigquery.Client(project=GCP_PROJECT_ID)
    print(f"✅ BigQuery connected: {GCP_PROJECT_ID}.{BQ_DATASET_ID}")
except Exception as e:
    print(f"❌ BigQuery Error: {e}")
    bq_client = None

# Try to initialize Redis client
redis_client = None
try:
    import redis as redis_lib
    redis_client = redis_lib.Redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    print(f"✅ Redis connected: {REDIS_URL}")
except Exception as e:
    print(f"⚠️  Redis unavailable ({e}), live feed disabled")
    redis_client = None

# ================== Helper: Dual Backend Query ==================#
def _bq_table(table: str) -> str:
    """Return fully-qualified BigQuery table path."""
    return f"`{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{table}`"


def query_db(sql_bq: str, params: tuple = None) -> pd.DataFrame:
    """
    Execute a query against BigQuery.
    """
    if not bq_client:
        raise RuntimeError("BigQuery client not initialized")
    
    # BQ query formatting (replace ? with params if any, though BQ usually uses named params)
    # For now, we assume sql_bq is already formatted or handles its own logic.
    return bq_client.query(sql_bq).to_dataframe()


def query_db_raw(sql_bq: str) -> list:
    """Execute BigQuery query and return raw list of tuples."""
    if not bq_client:
        return []
    
    rows = list(bq_client.query(sql_bq).result())
    return [tuple(row.values()) for row in rows]


def get_panorama_url(timestamp, bucket=None, path=None) -> str:
    """Return a GCS public URL for a panorama image, or None."""
    if path and bucket:
        return f"https://storage.googleapis.com/{bucket}/{path}"
    # Fallback logic is largely deprecated by unique GCS paths sent from C++ engine
    return None


# ================== Background Sink: Redis -> DB ==================#
async def sink_redis_to_db():
    """
    Background worker that drains Redis lists and populates BigQuery/SQLite.
    - waymo:frames_metadata -> frames table
    - waymo:edge_cases -> edge_cases table
    """
    print("🚀 Background Sink Task Started")
    while True:
        if not redis_client:
            await asyncio.sleep(60)
            continue
            
        try:
            # 1. Drain Frames Metadata
            # Use RPOP to get oldest first
            frame_data = redis_client.rpop("waymo:frames_metadata")
            if frame_data:
                payload = json.loads(frame_data)
                _insert_frame_meta(payload)
                
            # 2. Drain Edge Cases (Signal only)
            ec_data = redis_client.rpop("waymo:edge_cases_sink")
            if ec_data:
                payload = json.loads(ec_data)
                _insert_edge_case(payload)
                
            if not frame_data and not ec_data:
                await asyncio.sleep(2) # Wait for new records
        except Exception as e:
            print(f"❌ Sink Error: {e}")
            await asyncio.sleep(5)


def _insert_frame_meta(p):
    """Insert frame record into BigQuery."""
    if bq_client:
        try:
            table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.frames"
            query = f"""
                INSERT INTO `{table_id}` 
                (frame_id, timestamp, intent, speed_max, accel_x_min, accel_y_max, jerk_x_max, file_name, gcs_bucket, gcs_path)
                VALUES (
                    {p.get('frame_id')},
                    {p.get('timestamp')}, 
                    '{p.get('intent')}', 
                    {p.get('speed_max', p.get('speed'))}, 
                    {p.get('accel_x')}, 
                    {p.get('accel_y')}, 
                    {p.get('jerk_x')}, 
                    '{p.get('file_name')}', 
                    '{p.get('gcs_bucket')}', 
                    '{p.get('gcs_path')}'
                )
            """
            query_job = bq_client.query(query)
            query_job.result() # Wait for completion
        except Exception as e:
            print(f"⚠️ BQ Meta Insert Error: {e}")


def _insert_edge_case(p):
    """Insert edge case record into BigQuery."""
    if bq_client:
        try:
            table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.edge_cases"
            query = f"""
                INSERT INTO `{table_id}` (timestamp, type, severity, reason)
                VALUES (
                    {p.get('timestamp')}, 
                    'movement_anomaly', 
                    {p.get('accel')}, 
                    'accel: {p.get('accel')}, jerk: {p.get('jerk')}'
                )
            """
            query_job = bq_client.query(query)
            query_job.result()
        except Exception as e:
            print(f"⚠️ BQ EC Insert Error: {e}")


# ================== Debug Endpoints ==================#
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "backend": "bigquery" if bq_client else "sqlite",
        "redis": "connected" if redis_client else "disconnected",
    }


# ================== Batched Dashboard Summary ==================#
@app.get("/api/dashboard-summary")
async def get_dashboard_summary():
    """Fetch all dashboard data in a single request to avoid multiple roundtrips"""
    try:
        # Stats
        stats_rows = query_db_raw(
            "SELECT COUNT(*) FROM edge_cases",
            f"SELECT COUNT(*) FROM {_bq_table('edge_cases')}"
        )
        totalEdgeCases = stats_rows[0][0] if stats_rows else 0

        files_rows = query_db_raw(
            "SELECT COUNT(DISTINCT file_name) FROM frames",
            f"SELECT COUNT(DISTINCT file_name) FROM {_bq_table('frames')}"
        )
        filesProcessed = files_rows[0][0] if files_rows else 0

        types_count_rows = query_db_raw(
            "SELECT COUNT(DISTINCT edge_case_type) FROM edge_cases",
            f"SELECT COUNT(DISTINCT type) FROM {_bq_table('edge_cases')}"
        )
        edgeCaseTypes = types_count_rows[0][0] if types_count_rows else 0

        sev_rows = query_db_raw(
            "SELECT MAX(severity) FROM edge_cases",
            f"SELECT MAX(severity) FROM {_bq_table('edge_cases')}"
        )
        maxSeverity = sev_rows[0][0] or 0

        # Filters
        types_data = query_db_raw(
            "SELECT DISTINCT edge_case_type FROM edge_cases ORDER BY edge_case_type",
            f"SELECT DISTINCT type FROM {_bq_table('edge_cases')} ORDER BY type"
        )
        files_data = query_db_raw(
            "SELECT DISTINCT file_name FROM frames ORDER BY file_name",
            f"SELECT DISTINCT file_name FROM {_bq_table('frames')} ORDER BY file_name"
        )

        # Pie chart
        pie_data = query_db_raw(
            "SELECT edge_case_type as name, COUNT(*) as value FROM edge_cases GROUP BY edge_case_type",
            f"SELECT type as name, COUNT(*) as value FROM {_bq_table('edge_cases')} GROUP BY type"
        )

        # Intent chart
        intent_data = query_db_raw(
            "SELECT intent, COUNT(*) as count FROM frames GROUP BY intent ORDER BY count DESC",
            f"SELECT intent, COUNT(*) as count FROM {_bq_table('frames')} GROUP BY intent ORDER BY count DESC"
        )

        # Format pie chart
        colors = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", 
                  "var(--chart-4)", "var(--chart-5)", "var(--muted)"]
        pie_formatted = [
            {"name": row[0], "value": row[1], "fill": colors[i % len(colors)]}
            for i, row in enumerate(pie_data)
        ]
        
        intent_formatted = [
            {"intent": row[0] or "Unknown", "count": row[1]}
            for row in intent_data
        ]
        
        return {
            "stats": {
                "totalEdgeCases": totalEdgeCases,
                "filesProcessed": filesProcessed,
                "edgeCaseTypes": edgeCaseTypes,
                "maxSeverity": round(float(maxSeverity), 4)
            },
            "filters": {
                "types": [t[0] for t in types_data],
                "files": [f[0] for f in files_data]
            },
            "charts": {
                "pie": pie_formatted,
                "intent": intent_formatted
            }
        }
    except Exception as e:
        return {"error": str(e)}, 500


# ================== Ad-Hoc Queries ==================#
AD_HOC_QUERIES = {
    'hard_brake_while_turning_right': {
        'name': 'Hard Brake while Turning Right',
        'query': f"""
            SELECT frame_id, file_name, intent, accel_x_min, speed_max, timestamp, gcs_bucket, gcs_path
            FROM `{GCP_PROJECT_ID}.{BQ_DATASET_ID}.frames`
            WHERE intent = 'GO_RIGHT' AND accel_x_min < -0.8
            ORDER BY accel_x_min ASC
            LIMIT 25
        """
    },
    'high_lateral_accel_going_straight': {
        'name': 'High Lateral Accel. while Going Straight (Suspicious)',
        'query': f"""
            SELECT frame_id, file_name, intent, accel_y_max, speed_max, accel_x_min, timestamp, gcs_bucket, gcs_path
            FROM `{GCP_PROJECT_ID}.{BQ_DATASET_ID}.frames`
            WHERE intent = 'GO_STRAIGHT' AND accel_y_max > 0.6
            ORDER BY accel_y_max DESC
            LIMIT 25
        """
    },
    'high_jerk_at_low_speed': {
        'name': 'High Jerk at Low Speed (Stop-Go Traffic?)',
        'query': f"""
            SELECT frame_id, file_name, intent, jerk_x_max, speed_max, timestamp, gcs_bucket, gcs_path
            FROM `{GCP_PROJECT_ID}.{BQ_DATASET_ID}.frames`
            WHERE speed_max < 5.0 AND jerk_x_max > 0.4
            ORDER BY jerk_x_max DESC
            LIMIT 25
        """
    }
}


@app.get("/api/adhoc/queries")
async def get_adhoc_queries():
    return [
        {"value": key, "label": query_def['name']}
        for key, query_def in AD_HOC_QUERIES.items()
    ]


# ================== Stats & Filters ==================#
@app.get("/api/stats")
async def get_stats():
    try:
        totalEdgeCases = query_db_raw(f"SELECT COUNT(*) FROM {_bq_table('edge_cases')}")[0][0]
        filesProcessed = query_db_raw(f"SELECT COUNT(DISTINCT file_name) FROM {_bq_table('frames')}")[0][0]
        edgeCaseTypes = query_db_raw(f"SELECT COUNT(DISTINCT type) FROM {_bq_table('edge_cases')}")[0][0]
        maxSeverity = query_db_raw(f"SELECT MAX(severity) FROM {_bq_table('edge_cases')}")[0][0] or 0

        return {
            "totalEdgeCases": totalEdgeCases,
            "filesProcessed": filesProcessed,
            "edgeCaseTypes": edgeCaseTypes,
            "maxSeverity": round(float(maxSeverity), 4)
        }
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/filters")
async def get_filters():
    try:
        types = query_db_raw(f"SELECT DISTINCT type FROM {_bq_table('edge_cases')} ORDER BY type")
        files = query_db_raw(f"SELECT DISTINCT file_name FROM {_bq_table('frames')} ORDER BY file_name")
        return {
            "types": [t[0] for t in types],
            "files": [f[0] for f in files]
        }
    except Exception as e:
        return {"error": str(e)}, 500


# ================== Chart Endpoints ==================#
@app.get("/api/charts/pie")
async def get_pie_chart():
    try:
        data = query_db_raw(f"SELECT type as name, COUNT(*) as value FROM {_bq_table('edge_cases')} GROUP BY type")
        colors = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)",
                  "var(--chart-4)", "var(--chart-5)", "var(--muted)"]
        return [
            {"name": row[0], "value": row[1], "fill": colors[i % len(colors)]}
            for i, row in enumerate(data)
        ]
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/charts/histogram")
async def get_histogram_chart():
    try:
        df = query_db(f"SELECT severity FROM {_bq_table('edge_cases')}")
        counts, bins = np.histogram(df['severity'].dropna(), bins=30)
        return [
            {"range": f"{bins[i]:.2f}-{bins[i+1]:.2f}", "count": int(counts[i])}
            for i in range(len(bins) - 1)
        ]
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/charts/box-plot-data")
async def get_box_plot_data():
    try:
        df = query_db(f"SELECT type as edge_case_type, severity FROM {_bq_table('edge_cases')}")
        stats = df.groupby('edge_case_type')['severity'].describe()
        return [
            {
                "type": edge_case_type,
                "min": round(stats.loc[edge_case_type, 'min'], 4),
                "q1": round(stats.loc[edge_case_type, '25%'], 4),
                "median": round(stats.loc[edge_case_type, '50%'], 4),
                "q3": round(stats.loc[edge_case_type, '75%'], 4),
                "max": round(stats.loc[edge_case_type, 'max'], 4)
            }
            for edge_case_type in stats.index
        ]
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/charts/top-files")
async def get_top_files_chart():
    try:
        data = query_db_raw(f"""SELECT f.file_name as file, COUNT(ec.timestamp) as count 
                                FROM {_bq_table('frames')} f 
                                LEFT JOIN {_bq_table('edge_cases')} ec ON f.timestamp = ec.timestamp
                                GROUP BY f.file_name ORDER BY count DESC LIMIT 10""")
        return [{"file": row[0], "count": row[1]} for row in data]
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/charts/intent")
async def get_intent_chart():
    try:
        data = query_db_raw(
            "SELECT intent, COUNT(*) as count FROM frames GROUP BY intent ORDER BY count DESC",
            f"SELECT intent, COUNT(*) as count FROM {_bq_table('frames')} GROUP BY intent ORDER BY count DESC"
        )
        return [{"intent": row[0] or "Unknown", "count": int(row[1])} for row in data]
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/charts/scatter")
async def get_scatter_chart():
    try:
        df = query_db(
            """SELECT f.speed_max as speed, f.accel_x_min as accel, ec.severity,
                      ec.edge_case_type, f.file_name
               FROM edge_cases ec JOIN frames f ON ec.frame_table_id = f.id""",
            f"""SELECT f.speed_max as speed, f.accel_x_min as accel, ec.severity,
                       ec.type as edge_case_type, f.file_name
                FROM {_bq_table('edge_cases')} ec 
                JOIN {_bq_table('frames')} f ON ec.timestamp = f.timestamp"""
        )
        return [
            {
                "speed": round(float(row['speed']) if pd.notna(row['speed']) else 0, 2),
                "accel": round(float(row['accel']) if pd.notna(row['accel']) else 0, 2),
                "severity": round(float(row['severity']) if pd.notna(row['severity']) else 0, 2),
                "edge_case_type": row['edge_case_type'],
                "file_name": row['file_name']
            }
            for _, row in df.iterrows()
        ]
    except Exception as e:
        return {"error": str(e)}, 500


# ================== Query Endpoints ==================#
@app.get("/api/query/ad-hoc/{query_name}")
async def get_ad_hoc_query(query_name: str):
    try:
        if query_name not in AD_HOC_QUERIES:
            return {"error": f"Query '{query_name}' not found"}, 404

        query_def = AD_HOC_QUERIES[query_name]
        df = query_db(query_def['query'])

        data = df.to_dict('records')
        sanitized_data = [_sanitize_record(record) for record in data]
        
        # Add panorama URLs
        for record in sanitized_data:
             record['panorama_url'] = get_panorama_url(record.get('timestamp'), record.get('gcs_bucket'), record.get('gcs_path'))
             
        return sanitized_data
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/query/pre-flagged")
async def get_pre_flagged_data(page: int = 1):
    try:
        offset = (page - 1) * 25

        total_rows = query_db_raw(f"SELECT COUNT(*) as count FROM {_bq_table('edge_cases')}")
        total = int(total_rows[0][0])

        df = query_db(f"""SELECT f.timestamp AS frame_id, f.file_name, f.timestamp,
                               ec.type AS edge_case_type, ec.severity, ec.reason, f.intent,
                               f.speed_max, f.accel_x_min, f.accel_y_max, f.jerk_x_max,
                               f.gcs_bucket, f.gcs_path
                        FROM {_bq_table('edge_cases')} ec 
                        JOIN {_bq_table('frames')} f ON ec.timestamp = f.timestamp
                        ORDER BY ec.severity DESC LIMIT 25 OFFSET {offset}""")

        pages = (total + 24) // 25
        data = df.to_dict('records')

        sanitized_data = []
        for record in data:
            sanitized = _sanitize_record(record)
            
            # Add derived fields for the frontend
            sanitized['file'] = sanitized.get('file_name', '')
            if sanitized.get('speed_mean') is not None:
                sanitized['speed'] = f"{float(sanitized['speed_mean']):.2f}"
            else:
                sanitized['speed'] = '0.00'
            
            accel_vals = []
            for key in ['accel_x_min', 'accel_x_max', 'accel_y_min', 'accel_y_max']:
                val = sanitized.get(key)
                if val is not None:
                    try:
                        accel_vals.append(abs(float(val)))
                    except (ValueError, TypeError):
                        pass
            sanitized['accel'] = f"{max(accel_vals):.2f}" if accel_vals else '0.00'

            # Add GCS panorama URL
            sanitized['panorama_url'] = get_panorama_url(
                sanitized.get('timestamp'), 
                sanitized.get('gcs_bucket'), 
                sanitized.get('gcs_path')
            )

            sanitized_data.append(sanitized)

        return jsonable_encoder({
            "data": sanitized_data,
            "total": total,
            "page": page,
            "pages": pages
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}, 500


@app.get("/api/frame/{frame_id}")
async def get_frame_data(frame_id: int):
    try:
        # Note: frame_id here is usually the original dataset record index,
        # but in Phase 2 it's better to query by timestamp if possible.
        # However, interface expects /api/frame/{frame_id}.
        
        df = query_db(f"""SELECT f.frame_id, f.file_name, f.intent, f.timestamp,
                           f.speed_max, f.accel_x_min, f.accel_y_max, f.jerk_x_max,
                           f.gcs_bucket, f.gcs_path,
                           ec.type AS edge_case_type, ec.severity, ec.reason
                    FROM {_bq_table('frames')} f 
                    LEFT JOIN {_bq_table('edge_cases')} ec ON f.timestamp = ec.timestamp
                    WHERE f.frame_id = {frame_id}
                    LIMIT 1""")

        if df.empty:
            return {"error": "Frame not found"}, 404

        result = _sanitize_record(df.iloc[0].to_dict())

        # Add derived fields
        result['file'] = result.get('file_name', '')
        if result.get('speed_mean') is not None:
            result['speed'] = f"{float(result['speed_mean']):.2f}"
        else:
            result['speed'] = '0.00'

        accel_vals = []
        for key in ['accel_x_min', 'accel_x_max', 'accel_y_min', 'accel_y_max']:
            val = result.get(key)
            if val is not None:
                try:
                    accel_vals.append(abs(float(val)))
                except (ValueError, TypeError):
                    pass
        result['accel'] = f"{max(accel_vals):.2f}" if accel_vals else '0.00'

        # Add GCS panorama URL
        result['panorama_url'] = get_panorama_url(
            result.get('timestamp'),
            result.get('gcs_bucket'),
            result.get('gcs_path')
        )

        return jsonable_encoder(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}, 500


# ================== Live Redis Edge Case Stream (SSE) ==================#
@app.get("/api/live/edge-cases")
async def live_edge_cases():
    """
    Server-Sent Events (SSE) endpoint for real-time edge case signals.
    The C++ engine pushes edge cases to Redis via LPUSH to 'waymo:edge_cases'.
    This endpoint streams them to the frontend in real-time.
    """
    async def event_generator():
        last_len = 0
        while True:
            if not redis_client:
                yield f"data: {json.dumps({'error': 'Redis not connected'})}\n\n"
                await asyncio.sleep(10)
                continue

            try:
                current_len = redis_client.llen("waymo:edge_cases")
                if current_len > last_len:
                    # Fetch new items (LRANGE returns newest first since we LPUSH)
                    new_items = redis_client.lrange("waymo:edge_cases", 0, current_len - last_len - 1)
                    for item in reversed(new_items):
                        try:
                            parsed = json.loads(item)
                        except json.JSONDecodeError:
                            parsed = {"raw": item}
                        yield f"data: {json.dumps(parsed)}\n\n"
                    last_len = current_len
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

            await asyncio.sleep(2)  # Poll every 2 seconds

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/live/edge-cases/history")
async def get_edge_case_history(limit: int = 50):
    """Get recent edge cases from Redis (non-streaming)."""
    if not redis_client:
        return {"error": "Redis not connected", "data": []}
    
    try:
        items = redis_client.lrange("waymo:edge_cases", 0, limit - 1)
        parsed = []
        for item in items:
            try:
                parsed.append(json.loads(item))
            except json.JSONDecodeError:
                parsed.append({"raw": item})
        return {"data": parsed, "total": redis_client.llen("waymo:edge_cases")}
    except Exception as e:
        return {"error": str(e), "data": []}


# ================== Sanitization Helper ==================#
def _sanitize_record(record: dict) -> dict:
    """Sanitize a record dict for JSON serialization."""
    sanitized = {}
    for key, value in record.items():
        if value is None:
            sanitized[key] = None
        elif isinstance(value, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            sanitized[key] = int(value)
        elif isinstance(value, (np.floating, np.float64, np.float32)):
            sanitized[key] = float(value)
        elif isinstance(value, bytes):
            try:
                sanitized[key] = base64.b64encode(value).decode('utf-8')
            except Exception:
                sanitized[key] = None
        elif isinstance(value, float) and np.isnan(value):
            sanitized[key] = None
        else:
            sanitized[key] = value
    return sanitized


# ================== Agent Chat Endpoint ==================#
@app.post("/api/agent/chat")
async def agent_chat(request: dict):
    """Call the Waymo Agent for chat responses"""
    user_message = request.get("message", "")
    
    from Waymo_Agent.agent import root_agent
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
    from google.genai import types

    runner = Runner(
        app_name="Data Analyst",
        agent=root_agent,
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )

    session = await runner.session_service.create_session(
        app_name="Data Analyst",
        user_id="Dashboard User",
        state={}
    )

    content = types.Content(
        role='user',
        parts=[types.Part.from_text(text=user_message)]
    )

    response_text = ""
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=content
    ):
        if event.content:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text
    return {"response": response_text}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)