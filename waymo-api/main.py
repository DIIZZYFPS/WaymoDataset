import fastapi
import sqlite3
import numpy as np
import pandas as pd
import base64
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
import os

app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

default_db_path = os.path.join(os.getcwd(), "data", "edge_cases.db")
DB_PATH = os.getenv("DB_PATH", default_db_path)

print(f"📂 DATABASE SOURCE: {DB_PATH}")

# ================== Batched Dashboard Summary (Phase 2 Optimization) ==================#
@app.get("/api/dashboard-summary")
async def get_dashboard_summary():
    """Fetch all dashboard data in a single request to avoid multiple roundtrips"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Stats
        totalEdgeCases = cursor.execute("SELECT COUNT(*) FROM edge_cases").fetchone()[0]
        filesProcessed = cursor.execute("SELECT COUNT(DISTINCT file_name) FROM frames").fetchone()[0]  # ← Changed to frames table
        edgeCaseTypes = cursor.execute("SELECT COUNT(DISTINCT edge_case_type) FROM edge_cases").fetchone()[0]
        maxSeverity = cursor.execute("SELECT MAX(severity) FROM edge_cases").fetchone()[0] or 0
        
        # Filters
        types_data = cursor.execute("SELECT DISTINCT edge_case_type FROM edge_cases ORDER BY edge_case_type").fetchall()
        files_data = cursor.execute("SELECT DISTINCT file_name FROM frames ORDER BY file_name").fetchall()  # ← Changed to frames table
        
        # Pie chart
        pie_data = cursor.execute("SELECT edge_case_type as name, COUNT(*) as value FROM edge_cases GROUP BY edge_case_type").fetchall()
        
        # Intent chart - NO JOIN needed, just use frames table directly
        intent_data = cursor.execute("SELECT intent, COUNT(*) as count FROM frames GROUP BY intent ORDER BY count DESC").fetchall()
        
        conn.close()
        
        # Format pie chart
        colors = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", 
                  "var(--chart-4)", "var(--chart-5)", "var(--muted)"]
        pie_formatted = [
            {"name": row[0], "value": row[1], "fill": colors[i % len(colors)]}
            for i, row in enumerate(pie_data)
        ]
        
        # Format intent chart
        intent_formatted = [
            {"intent": row[0] or "Unknown", "count": row[1]}
            for row in intent_data
        ]
        
        return {
            "stats": {
                "totalEdgeCases": totalEdgeCases,
                "filesProcessed": filesProcessed,
                "edgeCaseTypes": edgeCaseTypes,
                "maxSeverity": round(maxSeverity, 4)
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

# Ad-hoc queries configuration
AD_HOC_QUERIES = {
    'hard_brake_while_turning_right': {
        'name': 'Hard Brake while Turning Right',
        'query': """
            SELECT frame_id, file_name, intent, accel_x_min, speed_max, panorama_thumbnail
            FROM frames
            WHERE intent = 'GO_RIGHT' AND accel_x_min < -0.8
            ORDER BY accel_x_min ASC
            LIMIT 25
        """
    },
    'high_lateral_accel_going_straight': {
        'name': 'High Lateral Accel. while Going Straight (Suspicious)',
        'query': """
            SELECT frame_id, file_name, intent, accel_y_max, speed_max, accel_x_min, panorama_thumbnail
            FROM frames
            WHERE intent = 'GO_STRAIGHT' AND accel_y_max > 0.6
            ORDER BY accel_y_max DESC
            LIMIT 25
        """
    },
    'high_jerk_at_low_speed': {
        'name': 'High Jerk at Low Speed (Stop-Go Traffic?)',
        'query': """
            SELECT frame_id, file_name, intent, jerk_x_max, speed_max, panorama_thumbnail
            FROM frames
            WHERE speed_max < 5.0 AND jerk_x_max > 0.4
            ORDER BY jerk_x_max DESC
            LIMIT 25
        """
    }
}

# ================== Debug Endpoints ==================#
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ================== Main API Endpoints ==================#

# Get available ad-hoc queries
@app.get("/api/adhoc/queries")
async def get_adhoc_queries():
    """Return list of available ad-hoc query options"""
    return [
        {"value": key, "label": query_def['name']}
        for key, query_def in AD_HOC_QUERIES.items()
    ]

# Stats and Filters
@app.get("/api/stats")
async def get_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        totalEdgeCases = cursor.execute("SELECT COUNT(*) FROM edge_cases").fetchone()[0]
        filesProcessed = cursor.execute("SELECT COUNT(DISTINCT file_name) FROM frames").fetchone()[0]  # ← Changed to frames table
        edgeCaseTypes = cursor.execute("SELECT COUNT(DISTINCT edge_case_type) FROM edge_cases").fetchone()[0]
        maxSeverity = cursor.execute("SELECT MAX(severity) FROM edge_cases").fetchone()[0] or 0
        
        conn.close()

        return {
            "totalEdgeCases": totalEdgeCases,
            "filesProcessed": filesProcessed,
            "edgeCaseTypes": edgeCaseTypes,
            "maxSeverity": round(maxSeverity, 4)
        }
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/filters")
async def get_filters():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        types = cursor.execute("SELECT DISTINCT edge_case_type FROM edge_cases ORDER BY edge_case_type").fetchall()
        files = cursor.execute("SELECT DISTINCT file_name FROM frames ORDER BY file_name").fetchall()  # ← Changed to frames table
        
        conn.close()

        return {
            "types": [t[0] for t in types],
            "files": [f[0] for f in files]
        }
    except Exception as e:
        return {"error": str(e)}, 500


# Charts
@app.get("/api/charts/pie")
async def get_pie_chart():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        data = cursor.execute(
            "SELECT edge_case_type as name, COUNT(*) as value FROM edge_cases GROUP BY edge_case_type"
        ).fetchall()
        
        conn.close()

        # Color palette for pie chart
        colors = [
            "var(--chart-1)",
            "var(--chart-2)",
            "var(--chart-3)",
            "var(--chart-4)",
            "var(--chart-5)",
            "var(--muted)",
        ]

        result = [
            {"name": row[0], "value": row[1], "fill": colors[i % len(colors)]}
            for i, row in enumerate(data)
        ]

        return result
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/charts/histogram")
async def get_histogram_chart():
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT severity FROM edge_cases", conn)
        conn.close()

        counts, bins = np.histogram(df['severity'].dropna(), bins=30)

        result = []
        for i in range(len(bins) - 1):
            range_str = f"{bins[i]:.2f}-{bins[i+1]:.2f}"
            result.append({"range": range_str, "count": int(counts[i])})

        return result
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/charts/box-plot-data")
async def get_box_plot_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT edge_case_type, severity FROM edge_cases", conn)
        conn.close()

        stats = df.groupby('edge_case_type')['severity'].describe()

        result = []
        for edge_case_type in stats.index:
            result.append({
                "type": edge_case_type,
                "min": round(stats.loc[edge_case_type, 'min'], 4),
                "q1": round(stats.loc[edge_case_type, '25%'], 4),
                "median": round(stats.loc[edge_case_type, '50%'], 4),
                "q3": round(stats.loc[edge_case_type, '75%'], 4),
                "max": round(stats.loc[edge_case_type, 'max'], 4)
            })

        return result
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/charts/top-files")
async def get_top_files_chart():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        data = cursor.execute(
            """
            SELECT f.file_name as file, COUNT(ec.id) as count 
            FROM frames f
            LEFT JOIN edge_cases ec ON f.id = ec.frame_table_id
            GROUP BY f.file_name 
            ORDER BY count DESC 
            LIMIT 10
            """
        ).fetchall()
        
        conn.close()

        result = [{"file": row[0], "count": row[1]} for row in data]
        return result
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/charts/intent")
async def get_intent_chart():
    try:
        conn = sqlite3.connect(DB_PATH)
        # FIXED: No JOIN needed - just query frames table directly
        df = pd.read_sql_query(
            "SELECT intent, COUNT(*) as count FROM frames GROUP BY intent ORDER BY count DESC",
            conn
        )
        conn.close()

        result = [{"intent": row[0], "count": int(row[1])} for row in df.values]
        return result
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/charts/scatter")
async def get_scatter_chart():
    try:
        conn = sqlite3.connect(DB_PATH)
        # FIXED: Use simple JOIN with frame_table_id
        df = pd.read_sql_query(
            """
            SELECT 
                f.speed_max as speed, 
                f.accel_x_min as accel, 
                ec.severity,
                ec.edge_case_type,
                f.file_name
            FROM edge_cases ec
            JOIN frames f ON ec.frame_table_id = f.id
            """,
            conn
        )
        conn.close()

        result = [
            {
                "speed": round(float(row[0]) if row[0] else 0, 2), 
                "accel": round(float(row[1]) if row[1] else 0, 2), 
                "severity": round(float(row[2]) if row[2] else 0, 2),
                "edge_case_type": row[3],
                "file_name": row[4]
            }
            for row in df.values
        ]
        return result
    except Exception as e:
        return {"error": str(e)}, 500


# Queries and Frames
@app.get("/api/query/ad-hoc/{query_name}")
async def get_ad_hoc_query(query_name: str):
    try:
        if query_name not in AD_HOC_QUERIES:
            return {"error": f"Query '{query_name}' not found"}, 404

        query = AD_HOC_QUERIES[query_name]['query']
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(query, conn)
        conn.close()

        # Convert DataFrame to dict and then sanitize all values
        data = df.to_dict('records')
        
        sanitized_data = []
        for record in data:
            sanitized_record = {}
            for key, value in record.items():
                # Handle None first
                if value is None:
                    sanitized_record[key] = None
                # Handle numpy integers
                elif isinstance(value, (np.integer, np.int64, np.int32, np.int16, np.int8)):
                    sanitized_record[key] = int(value)
                # Handle numpy floats
                elif isinstance(value, (np.floating, np.float64, np.float32)):
                    sanitized_record[key] = float(value)
                # Handle bytes
                elif isinstance(value, bytes):
                    try:
                        sanitized_record[key] = base64.b64encode(value).decode('utf-8')
                    except Exception:
                        sanitized_record[key] = None
                # Handle NaN
                elif isinstance(value, float) and np.isnan(value):
                    sanitized_record[key] = None
                # Keep everything else as is
                else:
                    sanitized_record[key] = value
            sanitized_data.append(sanitized_record)
        
        return sanitized_data
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/query/pre-flagged")
async def get_pre_flagged_data(page: int = 1):
    try:
        offset = (page - 1) * 25

        conn = sqlite3.connect(DB_PATH)
        
        # Get total count
        total_row = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM edge_cases", 
            conn
        )
        total = int(total_row['count'].iloc[0])
        
        # FIXED: Simple JOIN using frame_table_id
        df = pd.read_sql_query(
            """
            SELECT 
                ec.id,
                ec.frame_table_id AS frame_id,
                f.file_name,
                f.timestamp,
                ec.edge_case_type,
                ec.severity,
                ec.reason,
                f.intent,
                f.speed_min,
                f.speed_max,
                f.speed_mean,
                f.accel_x_min,
                f.accel_x_max,
                f.accel_y_min,
                f.accel_y_max,
                f.jerk_x_max,
                f.jerk_y_max,
                f.panorama_thumbnail
            FROM edge_cases ec
            JOIN frames f ON ec.frame_table_id = f.id
            ORDER BY ec.severity DESC
            LIMIT 25 OFFSET ?
            """,
            conn,
            params=(offset,)
        )
        
        conn.close()

        pages = (total + 24) // 25

        # Convert DataFrame to dict
        data = df.to_dict('records')
        
        # Sanitize all values - convert numpy types to native Python types
        sanitized_data = []
        for record in data:
            sanitized_record = {}
            for key, value in record.items():
                if value is None:
                    sanitized_record[key] = None
                elif isinstance(value, (np.integer, np.int64, np.int32, np.int16, np.int8)):
                    sanitized_record[key] = int(value)
                elif isinstance(value, (np.floating, np.float64, np.float32)):
                    sanitized_record[key] = float(value)
                elif isinstance(value, bytes):
                    try:
                        sanitized_record[key] = base64.b64encode(value).decode('utf-8')
                    except Exception:
                        sanitized_record[key] = None
                elif isinstance(value, float) and np.isnan(value):
                    sanitized_record[key] = None
                else:
                    sanitized_record[key] = value
            
            # Add derived fields for the frontend
            sanitized_record['file'] = sanitized_record.get('file_name', '')
            if sanitized_record.get('speed_mean') is not None:
                sanitized_record['speed'] = f"{sanitized_record['speed_mean']:.2f}"
            else:
                sanitized_record['speed'] = '0.00'
            
            accel_vals = []
            for key in ['accel_x_min', 'accel_x_max', 'accel_y_min', 'accel_y_max']:
                val = sanitized_record.get(key)
                if val is not None and not (isinstance(val, float) and np.isnan(val)):
                    accel_vals.append(abs(float(val)))
            
            if accel_vals:
                sanitized_record['accel'] = f"{max(accel_vals):.2f}"
            else:
                sanitized_record['accel'] = '0.00'
            
            sanitized_data.append(sanitized_record)
        
        # Use jsonable_encoder to convert any remaining numpy types
        result = {
            "data": sanitized_data,
            "total": total,
            "page": page,
            "pages": pages
        }
        return jsonable_encoder(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}, 500


@app.get("/api/frame/{frame_id}")
async def get_frame_data(frame_id: int, file_name: str = None):
    """
    Get frame data by frame_id.
    If file_name is provided, returns specific frame from that file.
    Otherwise returns first match (may not be what you want if frame_id exists in multiple files).
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.row_factory = sqlite3.Row
        
        # FIXED: Simple JOIN using frame_table_id
        if file_name:
            cursor.execute(
                """
                SELECT 
                    f.id,
                    f.frame_id,
                    f.file_name,
                    f.intent,
                    f.speed_min,
                    f.speed_max,
                    f.speed_mean,
                    f.accel_x_min,
                    f.accel_x_max,
                    f.accel_y_min,
                    f.accel_y_max,
                    f.jerk_x_max,
                    f.jerk_y_max,
                    f.panorama_thumbnail,
                    ec.edge_case_type,
                    ec.severity,
                    ec.reason
                FROM frames f
                LEFT JOIN edge_cases ec ON f.id = ec.frame_table_id
                WHERE f.frame_id = ? AND f.file_name = ?
                """,
                (frame_id, file_name)
            )
        else:
            cursor.execute(
                """
                SELECT 
                    f.id,
                    f.frame_id,
                    f.file_name,
                    f.intent,
                    f.speed_min,
                    f.speed_max,
                    f.speed_mean,
                    f.accel_x_min,
                    f.accel_x_max,
                    f.accel_y_min,
                    f.accel_y_max,
                    f.jerk_x_max,
                    f.jerk_y_max,
                    f.panorama_thumbnail,
                    ec.edge_case_type,
                    ec.severity,
                    ec.reason
                FROM frames f
                LEFT JOIN edge_cases ec ON f.id = ec.frame_table_id
                WHERE f.frame_id = ?
                LIMIT 1
                """,
                (frame_id,)
            )
        
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"error": "Frame not found"}, 404

        result = dict(row)
        
        # Convert numpy types and thumbnail blob
        for key, value in result.items():
            if isinstance(value, (np.integer, np.int64, np.int32, np.int16, np.int8)):
                result[key] = int(value)
            elif isinstance(value, (np.floating, np.float64, np.float32)):
                result[key] = float(value)
            elif isinstance(value, bytes) and key == 'panorama_thumbnail' and value is not None:
                # Only encode if thumbnail exists (skip NULL values)
                try:
                    result[key] = base64.b64encode(value).decode('utf-8')
                except Exception:
                    result[key] = None
            elif pd.isna(value):
                result[key] = None
        
        # Add derived fields for the frontend
        result['file'] = result.get('file_name', '')
        if result.get('speed_mean') is not None:
            result['speed'] = f"{result['speed_mean']:.2f}"
        else:
            result['speed'] = '0.00'
        
        accel_vals = []
        for key in ['accel_x_min', 'accel_x_max', 'accel_y_min', 'accel_y_max']:
            val = result.get(key)
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                accel_vals.append(abs(float(val)))
        
        if accel_vals:
            result['accel'] = f"{max(accel_vals):.2f}"
        else:
            result['accel'] = '0.00'

        return jsonable_encoder(result)
    except Exception as e:
        return {"error": str(e)}, 500


# ================== Agent Chat Endpoint (Sample) ==================#
@app.post("/api/agent/chat")
async def agent_chat(request: dict):
    """Call the Waymo Agent for chat responses"""
    user_message = request.get("message", "")
    
    from Waymo_Agent.agent import root_agent
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
    from google.genai import types

    #Create Runner
    runner = Runner(
        app_name = "Data Analyst",
        agent = root_agent,
        session_service = InMemorySessionService(),
        memory_service = InMemoryMemoryService(),
    )

    #Create session
    session = await runner.session_service.create_session(
        app_name = "Data Analyst",
        user_id = "Dashboard User",
        state = {}
    )

    #Create message
    content = types.Content(
        role = 'user',
        parts = [types.Part.from_text(text = user_message)]
    )

    #Get response
    response_text = ""
    async for event in runner.run_async(
        user_id = session.user_id,
        session_id = session.id,
        new_message = content
    ):
        if event.content:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text
    return {"response": response_text}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)