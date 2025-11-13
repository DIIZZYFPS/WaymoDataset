from google.adk.agents.llm_agent import Agent
from google.adk.tools import FunctionTool
import sqlite3
import pandas as pd
import base64
import math  # ← Add this for STDEV function
import re
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from parent directory (waymo-api/.env)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configure Gemini for vision analysis
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError(f"GOOGLE_API_KEY not found! Checked .env at: {env_path}")

client = genai.Client(api_key=api_key)

DB_PATH = "../waymo_dataset/results/edge_cases.db"

def _register_custom_functions(conn):
    """Register custom statistical functions for SQLite"""
    
    # Standard deviation function
    class StdevFunc:
        def __init__(self):
            self.values = []
        
        def step(self, value):
            if value is not None:
                self.values.append(value)
        
        def finalize(self):
            if len(self.values) < 2:
                return None
            mean = sum(self.values) / len(self.values)
            variance = sum((x - mean) ** 2 for x in self.values) / (len(self.values) - 1)
            return math.sqrt(variance)
    
    conn.create_aggregate("STDEV", 1, StdevFunc)
    
    # Variance function
    class VarianceFunc:
        def __init__(self):
            self.values = []
        
        def step(self, value):
            if value is not None:
                self.values.append(value)
        
        def finalize(self):
            if len(self.values) < 2:
                return None
            mean = sum(self.values) / len(self.values)
            return sum((x - mean) ** 2 for x in self.values) / (len(self.values) - 1)
    
    conn.create_aggregate("VARIANCE", 1, VarianceFunc)
    
    # Median function (SQLite has this in newer versions, but we'll add it for safety)
    class MedianFunc:
        def __init__(self):
            self.values = []
        
        def step(self, value):
            if value is not None:
                self.values.append(value)
        
        def finalize(self):
            if not self.values:
                return None
            sorted_values = sorted(self.values)
            n = len(sorted_values)
            if n % 2 == 0:
                return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
            else:
                return sorted_values[n//2]
    
    conn.create_aggregate("MEDIAN", 1, MedianFunc)


def execute_sql_query(sql_query: str) -> str:
    """Execute a READ-ONLY SQL query against the Waymo edge cases database and return results as JSON string.
    Only SELECT queries are allowed. DO NOT select panorama_thumbnail column.
    """
    if not sql_query.strip().lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")
    
    # Check for panorama_thumbnail or SELECT *
    query_lower = sql_query.lower()
    
    # Block panorama_thumbnail explicitly
    if 'panorama_thumbnail' in query_lower:
        raise ValueError("Cannot select 'panorama_thumbnail' column. Use classify_image(frame_id) instead for image analysis.")
    
    # Block SELECT * from frames table (could include panorama_thumbnail)
    if re.search(r'select\s+\*\s+from\s+frames', query_lower):
        raise ValueError("Cannot use 'SELECT * FROM frames' as it includes the panorama_thumbnail BLOB. Please specify columns explicitly, excluding panorama_thumbnail.")
    
    # Block f.* when f is aliased to frames
    if re.search(r'from\s+frames\s+(?:as\s+)?(\w+)', query_lower):
        alias_match = re.search(r'from\s+frames\s+(?:as\s+)?(\w+)', query_lower)
        if alias_match:
            alias = alias_match.group(1)
            # Check if query uses alias.*
            if re.search(rf'\b{alias}\.\*', query_lower):
                raise ValueError(f"Cannot use '{alias}.*' as it includes the panorama_thumbnail BLOB. Please specify columns explicitly, excluding panorama_thumbnail.")
    
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    try:
        # Register custom statistical functions
        _register_custom_functions(conn)
        
        df = pd.read_sql_query(sql_query, conn)
        return df.to_json(orient="records")
    finally:
        conn.close()



def classify_image(frame_id: int) -> str:
    """
    Retrieve and analyze a frame's panorama thumbnail using Gemini Vision.
    
    Args:
        frame_id: The frame_id to retrieve and analyze the image for
        
    Returns:
        String containing both the vision analysis and the frame metadata
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    try:
        cursor = conn.cursor()
        
        # Query to get the image BLOB and frame metadata
        query = """
        SELECT 
            f.frame_id,
            f.file_name,
            f.intent,
            f.speed_max,
            f.accel_x_min,
            f.accel_y_max,
            f.jerk_x_max,
            f.panorama_thumbnail,
            ec.edge_case_type,
            ec.severity
        FROM frames f
        LEFT JOIN edge_cases ec ON f.id = ec.frame_table_id
        WHERE f.id = ?
        LIMIT 1
        """
        
        cursor.execute(query, (frame_id,))
        row = cursor.fetchone()
        
        if not row:
            return f"Error: Frame {frame_id} not found in database"
        
        # Unpack the row
        (frame_id, file_name, intent, speed_max, accel_x_min, 
         accel_y_max, jerk_x_max, panorama_blob, edge_case_type, severity) = row
        
        if not panorama_blob:
            return f"Error: Frame {frame_id} has no panorama thumbnail"
        
        # Convert BLOB to base64 string for Gemini Vision API
        if isinstance(panorama_blob, str):
            # Already base64, use directly
            image_base64 = panorama_blob
        else:
            # If it's raw bytes, encode to base64
            image_base64 = base64.b64encode(panorama_blob).decode('utf-8')
        
        # Create a detailed prompt with context
        vision_prompt = f"""Analyze this panorama image from an autonomous vehicle's camera system.

Frame Context:
- Frame ID: {frame_id}
- File: {file_name}
- Driving Intent: {intent}
- Speed: {speed_max:.2f} m/s ({speed_max * 3.6:.1f} km/h)
- Longitudinal Accel: {accel_x_min:.3f} m/s² (negative = braking)
- Lateral Accel: {accel_y_max:.3f} m/s² (high value = swerve)
- Jerk: {jerk_x_max:.3f} m/s³
- Edge Case Type: {edge_case_type or 'None'}
- Severity: {severity or 'N/A'}

Please describe:
1. What objects/obstacles are visible in the scene (vehicles, pedestrians, cyclists, traffic signs, road conditions)
2. The spatial relationship between the ego vehicle and surrounding objects
3. Any potential hazards or unusual situations
4. How the visual scene correlates with the motion data (e.g., why might the vehicle have braked hard or swerved)
5. Traffic conditions and road environment

Be specific and detailed, focusing on safety-critical elements."""

        # Use Gemini Vision API with inline data
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=[
                types.Content(
                    parts=[
                        types.Part(text=vision_prompt),
                        types.Part(
                            inline_data=types.Blob(
                                mime_type='image/jpeg',
                                data=image_base64
                            )
                        )
                    ]
                )
            ]
        )
        
        # Combine vision analysis with metadata
        result = f"""VISION ANALYSIS FOR FRAME {frame_id}:

{response.text}

MOTION DATA SUMMARY:
- Intent: {intent}
- Speed: {speed_max:.2f} m/s ({speed_max * 3.6:.1f} km/h)
- Longitudinal Acceleration: {accel_x_min:.3f} m/s² {"(HARD BRAKING)" if accel_x_min < -0.8 else ""}
- Lateral Acceleration: {accel_y_max:.3f} m/s² {"(EVASIVE MANEUVER)" if accel_y_max > 0.6 else ""}
- Jerk: {jerk_x_max:.3f} m/s³
- Edge Case: {edge_case_type or "None detected"}
- Severity: {severity if severity else "N/A"}
"""
        
        return result
        
    except Exception as e:
        return f"Error analyzing image for frame {frame_id}: {str(e)}"
    finally:
        conn.close()


root_agent = Agent(
    model='gemini-2.5-flash',
    name='Waymo_Data_Analyst',
    description='A Data Analyst specializing in vehicle motion data with vision capabilities.',
    instruction="""You are an expert-level Waymo Data Analyst. Your purpose is to answer natural language questions about vehicle motion data by converting them into precise SQLite queries AND analyzing panorama images from specific frames.

You have two tools:
1. execute_sql_query(sql_query: str) - For querying the database
2. classify_image(frame_id: int) - For analyzing panorama images using Gemini Vision

WHEN TO USE EACH TOOL:

Use execute_sql_query for data analysis, statistics, filtering, aggregations.
Use classify_image when the user asks about:
  - What does frame X look like?
  - Analyze the image for frame Y
  - Show me what's happening in frame Z
  - What caused the edge case in frame X? (the tool will provide both visual analysis AND motion data)

DATABASE SCHEMA:

Table 1: frames
  - id (INTEGER PRIMARY KEY AUTOINCREMENT): Globally unique frame ID (use this for JOINs!)
  - frame_id (INTEGER): Frame number within the source file (NOT unique across files!)
  - file_name (TEXT): Source tfrecord file name
  - timestamp (INTEGER): Unix timestamp in microseconds
  - intent (TEXT): Driving intent (e.g., GO_STRAIGHT, GO_LEFT, GO_RIGHT)
  - speed_min (REAL): Minimum speed in m/s
  - speed_max (REAL): Maximum speed in m/s
  - speed_mean (REAL): Mean speed in m/s
  - accel_x_min (REAL): CRITICAL - Minimum longitudinal acceleration (m/s²). A large negative value (e.g., < -0.8) indicates HARD BRAKING
  - accel_x_max (REAL): Maximum longitudinal acceleration (m/s²)
  - accel_y_min (REAL): Minimum lateral acceleration (m/s²)
  - accel_y_max (REAL): CRITICAL - Maximum lateral acceleration (m/s²). A large positive value (e.g., > 0.6) indicates a SWERVE or EVASIVE MANEUVER
  - jerk_x_max (REAL): Maximum longitudinal jerk (m/s³)
  - jerk_y_max (REAL): Maximum lateral jerk (m/s³)
  - panorama_thumbnail (BLOB): WARNING - NEVER SELECT THIS COLUMN IN SQL QUERIES. Use classify_image tool instead.
  - created_at (TEXT): Timestamp when the frame was created. Irrelevant for queries.

Table 2: edge_cases
  - id (INTEGER PRIMARY KEY AUTOINCREMENT): Unique edge case ID
  - frame_table_id (INTEGER NOT NULL): Foreign key to frames.id (THIS IS THE JOIN KEY!)
  - edge_case_type (TEXT): The type of event (e.g., hard_brake, evasive_maneuver, high_jerk)
  - severity (REAL): A severity score 0.0-1.0 (normalized, where 1.0 = extreme)
  - reason (TEXT): Human-readable reasoning for the event with actual threshold values
  - created_at (TEXT): Timestamp when the edge case was created. Irrelevant for queries.

CRITICAL SQL RULES:

1. JOIN KEY: Always join on frames.id = edge_cases.frame_table_id (simple foreign key!)
   
   CORRECT:
   SELECT f.frame_id, f.speed_max, ec.severity
   FROM frames f
   JOIN edge_cases ec ON f.id = ec.frame_table_id
   
   WRONG:
   JOIN edge_cases ec ON f.frame_id = ec.frame_id  ← DON'T USE frame_id for JOIN!

2. NEVER USE SELECT STAR: You MUST explicitly list columns. Using SELECT * or f.* will cause errors because it includes the panorama_thumbnail BLOB.

3. NEVER SELECT panorama_thumbnail: This column contains binary image data. Use the classify_image(frame_id) tool instead.

4. ALWAYS SPECIFY COLUMNS: Example - SELECT f.frame_id, f.file_name, f.intent, f.speed_max, f.accel_x_min, ec.severity FROM frames f ...

5. DEFAULTS: Always LIMIT your queries to 25 rows unless the user asks for more.

6. SUPPORTED AGGREGATE FUNCTIONS:
   - Standard: COUNT, SUM, AVG, MIN, MAX
   - Statistical: STDEV (standard deviation), VARIANCE, MEDIAN
   - String: GROUP_CONCAT (concatenates values with separator)

7. RESPONSE FORMAT: First call the appropriate tool. Second, provide a natural language answer based on the results. The classify_image tool will give you a complete analysis already.

USAGE EXAMPLES:

User asks: How many total hard brakes are recorded?
You should: execute_sql_query("SELECT COUNT(*) FROM edge_cases WHERE edge_case_type = 'hard_brake'")

User asks: Show me high severity frames
You should: execute_sql_query("SELECT f.frame_id, f.file_name, f.intent, f.speed_max, ec.severity FROM frames f JOIN edge_cases ec ON f.id = ec.frame_table_id WHERE ec.severity > 0.8 LIMIT 25")

User asks: What's the standard deviation of severity scores?
You should: execute_sql_query("SELECT MIN(severity) AS min_severity, MAX(severity) AS max_severity, AVG(severity) AS avg_severity, STDEV(severity) AS stdev_severity FROM edge_cases")

User asks: What does frame 123 look like?
You should: classify_image(123) - This will automatically analyze the image and provide both visual description and motion data

User asks: Why did frame 456 have high severity?
You should: classify_image(456) - This will provide complete visual and motion analysis explaining the cause

User asks: Show me frames with hard brakes while turning left
You should: execute_sql_query("SELECT f.frame_id, f.file_name, f.intent, f.accel_x_min, ec.severity FROM frames f JOIN edge_cases ec ON f.id = ec.frame_table_id WHERE f.intent = 'GO_LEFT' AND ec.edge_case_type = 'hard_brake' ORDER BY ec.severity DESC LIMIT 25")
""",
    tools=[
        FunctionTool(execute_sql_query),
        FunctionTool(classify_image)
    ]
)
