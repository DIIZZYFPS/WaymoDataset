from google.adk.agents.llm_agent import Agent
from google.adk.tools import FunctionTool
from google.cloud import bigquery
from google.cloud import storage
import pandas as pd
import base64
import os
import re
from google import genai
from google.genai import types
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# GCP Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "waymo-dataset-scale")
DATASET_ID = os.getenv("BQ_DATASET_ID", "waymo_analytics")
IMAGE_BUCKET = os.getenv("GCS_IMAGE_BUCKET", "waymo-processed-images")

# Clients
bq_client = bigquery.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)
genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def execute_query(sql_query: str) -> str:
    """Execute a READ-ONLY SQL query against BigQuery and return results as JSON string.
    Only SELECT queries are allowed.
    """
    if not sql_query.strip().lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")
    
    # Simple security check for projection
    if '*' in sql_query.lower():
         raise ValueError("Cannot use SELECT *. Please specify columns explicitly for safety and cost.")

    try:
        # Use the configured dataset if not specified in query
        if f"{PROJECT_ID}.{DATASET_ID}" not in sql_query:
            # Basic attempt to inject dataset if missing
            sql_query = sql_query.replace("FROM frames", f"FROM `{PROJECT_ID}.{DATASET_ID}.frames`").replace("FROM edge_cases", f"FROM `{PROJECT_ID}.{DATASET_ID}.edge_cases`")

        query_job = bq_client.query(sql_query)
        df = query_job.to_dataframe()
        return df.to_json(orient="records")
    except Exception as e:
        return f"BigQuery Error: {str(e)}"

def classify_image(timestamp: int) -> str:
    """
    Retrieve and analyze a frame's panorama thumbnail from GCS using Gemini Vision.
    
    Args:
        timestamp: The timestamp (microseconds) to retrieve the image for (from the BigQuery metadata)
        
    Returns:
        String containing both the vision analysis and the frame metadata
    """
    try:
        # 1. Fetch metadata from BigQuery
        query = f"""
        SELECT 
            timestamp, intent, speed_max, accel_x_min, accel_y_max, jerk_x_max
        FROM `{PROJECT_ID}.{DATASET_ID}.frames`
        WHERE timestamp = {timestamp}
        LIMIT 1
        """
        df = bq_client.query(query).to_dataframe()
        
        if df.empty:
            return f"Error: Frame at {timestamp} not found in BigQuery"
            
        row = df.iloc[0]
        
        # 2. Fetch image from GCS
        bucket = storage_client.bucket(IMAGE_BUCKET)
        blob_name = f"panoramas/{timestamp}.jpg"
        blob = bucket.blob(blob_name)
        
        if not blob.exists():
            return f"Error: Image {blob_name} not found in GCS bucket {IMAGE_BUCKET}"
            
        image_bytes = blob.download_as_bytes()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # 3. Analyze with Gemini
        vision_prompt = f"""Analyze this high-resolution panorama from Waymo's C++ Streaming Engine.
        
Frame Context (High Scale):
- Timestamp: {timestamp}
- Driving Intent: {row['intent']}
- Speed: {row['speed_max']:.2f} m/s
- Longitudinal Accel: {row['accel_x_min']:.3f} m/s²
- Lateral Accel: {row['accel_y_max']:.3f} m/s²
- Jerk: {row['jerk_x_max']:.3f} m/s³

Please describe the scene and correlate with motion data."""

        response = genai_client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=[
                types.Content(parts=[
                    types.Part(text=vision_prompt),
                    types.Part(inline_data=types.Blob(mime_type='image/jpeg', data=image_base64))
                ])
            ]
        )
        
        return f"VISION ANALYSIS:\n{response.text}\n\nMETADATA: {row.to_json()}"
        
    except Exception as e:
        return f"Error during GCS/BQ analysis: {str(e)}"

root_agent = Agent(
    model='gemini-2.5-flash',
    name='Waymo_Data_Analyst_v2',
    description='A Data Analyst specializing in high-scale vehicle motion data with vision capabilities.',
    instruction=f"""You are an expert-level Waymo Data Analyst. Your purpose is to answer natural language questions about vehicle motion data by converting them into BigQuery SQL AND analyzing panorama images from GCS.

You have two tools:
1. execute_query(sql_query: str) - For querying BigQuery (Dataset: {PROJECT_ID}.{DATASET_ID})
2. classify_image(timestamp: int) - For analyzing panorama images using Gemini Vision

SCHEMA:
- `{PROJECT_ID}.{DATASET_ID}.frames`: timestamp (INT64), intent (STRING), speed_max (FLOAT64), accel_x_min (FLOAT64), accel_y_max (FLOAT64), jerk_x_max (FLOAT64)
- `{PROJECT_ID}.{DATASET_ID}.edge_cases`: timestamp (INT64), type (STRING), severity (FLOAT64)

RULES:
1. Always use the full table paths: `{PROJECT_ID}.{DATASET_ID}.frames`.
2. Use `timestamp` for JOINs and for the `classify_image` tool.
3. LIMIT queries to 25 rows unless asked for more.
""",
    tools=[
        FunctionTool(execute_query),
        FunctionTool(classify_image)
    ]
)
