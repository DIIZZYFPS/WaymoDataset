import sys
import tensorflow as tf
from waymo_open_dataset.protos import end_to_end_driving_data_pb2 as wod_e2ed_pb2
import numpy as np
import sqlite3
import os
import json
from datetime import datetime
import cv2
import io

# ============================================================================
# CONFIGURATION
# ============================================================================
# Use environment variable if set, otherwise use default
RESULTS_DIR = os.getenv('RESULTS_DIR', './waymo_dataset/results')

DB_PATH = os.path.join(RESULTS_DIR, 'edge_cases.db')
THRESHOLD_FILE = os.path.join(RESULTS_DIR, 'thresholds.json')

# Ensure directories exist
os.makedirs(RESULTS_DIR, exist_ok=True)

# Default industry-standard thresholds
DEFAULT_THRESHOLDS = {
    'hard_brake': -0.8,      # Moderate to hard braking
    'lateral': 0.6,          # Evasive maneuver (lateral G-force)
    'jerk': 0.4              # Sudden acceleration change
}

# ============================================================================
# SEVERITY NORMALIZATION
# ============================================================================
def calculate_normalized_severity(raw_value, threshold, is_negative=False):
    """
    Normalize severity to 0-1 scale based on distance from threshold.
    
    Args:
        raw_value: The measured value
        threshold: Threshold value (edge of "normal" range)
        is_negative: True if threshold is for negative values (like braking)
    
    Returns:
        Severity score 0.0-1.0 where:
        - 0.0 = at threshold (barely an edge case)
        - 1.0 = 3x beyond threshold (extremely severe)
    
    Examples:
        Hard brake at -0.4 with threshold -0.375:
            severity = (0.4 - 0.375) / (1.125 - 0.375) = 0.033 (very mild)
        
        Hard brake at -1.5 with threshold -0.375:
            severity = (1.5 - 0.375) / (1.125 - 0.375) = 1.0 (extreme)
    """
    if is_negative:
        # For hard braking: more negative = more severe
        raw_abs = abs(raw_value)
        threshold_abs = abs(threshold)
        
        # If not beyond threshold, shouldn't be flagged (safety check)
        if raw_abs < threshold_abs:
            return 0.0
        
        # Severity increases as we go beyond threshold
        # Cap at 3x threshold for normalization (anything beyond = severity 1.0)
        max_expected = threshold_abs * 3
        severity = (raw_abs - threshold_abs) / (max_expected - threshold_abs)
    else:
        # For lateral/jerk: higher value = more severe
        if raw_value < threshold:
            return 0.0
        
        # Cap at 3x threshold
        max_expected = threshold * 3
        severity = (raw_value - threshold) / (max_expected - threshold)
    
    # Clamp to [0, 1]
    return max(0.0, min(severity, 1.0))

# ============================================================================
# DATABASE SETUP
# ============================================================================
def init_database(db_path):
    """Initialize SQLite database for comprehensive motion data storage."""
    try:
        # Use check_same_thread=False for container compatibility
        conn = sqlite3.connect(db_path, check_same_thread=False, timeout=10.0)
        conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging for better concurrency
        cursor = conn.cursor()
        
        # Main frames table - stores ALL frame motion data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frame_id INTEGER,
                file_name TEXT,
                timestamp BIGINT,
                intent TEXT,
                speed_min REAL,
                speed_max REAL,
                speed_mean REAL,
                accel_x_min REAL,
                accel_x_max REAL,
                accel_y_min REAL,
                accel_y_max REAL,
                jerk_x_max REAL,
                jerk_y_max REAL,
                panorama_thumbnail BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Edge cases table - SIMPLIFIED: just reference frames.id (globally unique!)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS edge_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frame_table_id INTEGER NOT NULL,
                edge_case_type TEXT,
                severity REAL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(frame_table_id) REFERENCES frames(id)
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_frames_intent ON frames(intent)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_frames_accel_x_min ON frames(accel_x_min)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_frames_accel_y_max ON frames(accel_y_max)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edge_cases_type ON edge_cases(edge_case_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edge_cases_frame ON edge_cases(frame_table_id)')
        
        conn.commit()
        return conn
    except Exception as e:
        print(f"✗ Database initialization error: {e}")
        raise

def store_frame_data(conn, frame_id, file_name, timestamp, motion_data, intent, panorama_thumbnail_bytes=None):
    """Store complete motion profile for every frame and return the database row ID."""
    try:
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO frames 
            (frame_id, file_name, timestamp, intent, speed_min, speed_max, speed_mean, 
             accel_x_min, accel_x_max, accel_y_min, accel_y_max, jerk_x_max, jerk_y_max, panorama_thumbnail)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            frame_id,
            file_name,
            timestamp,
            intent,
            motion_data['speed_min'],
            motion_data['speed_max'],
            motion_data['speed_mean'],
            motion_data['accel_x_min'],
            motion_data['accel_x_max'],
            motion_data['accel_y_min'],
            motion_data['accel_y_max'],
            motion_data['jerk_x_max'],
            motion_data['jerk_y_max'],
            panorama_thumbnail_bytes
        ))
        
        conn.commit()
        
        # Return the auto-increment ID of the inserted row
        return cursor.lastrowid
        
    except sqlite3.OperationalError as e:
        print(f"✗ Database write error: {e}")
        try:
            conn.rollback()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO frames 
                (frame_id, file_name, timestamp, intent, speed_min, speed_max, speed_mean, 
                 accel_x_min, accel_x_max, accel_y_min, accel_y_max, jerk_x_max, jerk_y_max, panorama_thumbnail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                frame_id,
                file_name,
                timestamp,
                intent,
                motion_data['speed_min'],
                motion_data['speed_max'],
                motion_data['speed_mean'],
                motion_data['accel_x_min'],
                motion_data['accel_x_max'],
                motion_data['accel_y_min'],
                motion_data['accel_y_max'],
                motion_data['jerk_x_max'],
                motion_data['jerk_y_max'],
                panorama_thumbnail_bytes
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as retry_err:
            print(f"  ✗ Retry failed: {retry_err}")
            return None

def store_edge_case(conn, frame_table_id, edge_case_type, severity, reason):
    """Store flagged edge case to database using frames.id as foreign key."""
    try:
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO edge_cases 
            (frame_table_id, edge_case_type, severity, reason)
            VALUES (?, ?, ?, ?)
        ''', (
            frame_table_id,
            edge_case_type,
            severity,
            reason
        ))
        
        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"✗ Database write error: {e}")
        try:
            conn.rollback()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO edge_cases 
                (frame_table_id, edge_case_type, severity, reason)
                VALUES (?, ?, ?, ?)
            ''', (
                frame_table_id,
                edge_case_type,
                severity,
                reason
            ))
            conn.commit()
        except Exception as retry_err:
            print(f"  ✗ Retry failed: {retry_err}")

# ============================================================================
# IMAGE STITCHING & THUMBNAIL GENERATION
# ============================================================================
def stitch_panorama(camera_images_dict, width=4096):
    """
    Stitch front 3 camera images into panorama.
    
    Focus on FRONT_LEFT, FRONT_CENTER, FRONT_RIGHT which are the primary driving cameras.
    This matches the Waymo tutorial approach for front-facing 180° panorama.
    
    Args:
        camera_images_dict: Dict of camera images {camera_name: image_array}
        width: Output panorama width in pixels
    
    Returns:
        panorama: Stitched image array
    """
    try:
        # Ensure we have the three front cameras (matching tutorial naming)
        front_cams = {
            'FRONT_LEFT': camera_images_dict.get('FRONT_LEFT'),
            'FRONT_CENTER': camera_images_dict.get('FRONT_CENTER'),
            'FRONT_RIGHT': camera_images_dict.get('FRONT_RIGHT')
        }
        
        valid_cams = {k: v for k, v in front_cams.items() if v is not None and isinstance(v, np.ndarray)}
        
        if len(valid_cams) == 0:
            return None
        
        # Get reference height from first valid image
        ref_height = None
        for img in valid_cams.values():
            if img is not None:
                ref_height = img.shape[0]
                break
        
        if ref_height is None:
            return None
        
        # Resize all front cameras to reference height while maintaining aspect ratio
        resized_front = {}
        for cam_name in ['FRONT_LEFT', 'FRONT_CENTER', 'FRONT_RIGHT']:
            img = front_cams.get(cam_name)
            if img is not None and isinstance(img, np.ndarray):
                h, w = img.shape[:2]
                if h > 0:
                    # Maintain aspect ratio
                    new_w = int(w * (ref_height / h))
                    resized_img = cv2.resize(img, (new_w, ref_height))
                    resized_front[cam_name] = resized_img
                else:
                    resized_front[cam_name] = np.zeros((ref_height, 400, 3), dtype=np.uint8)
            else:
                resized_front[cam_name] = np.zeros((ref_height, 400, 3), dtype=np.uint8)
        
        # Stitch the 3 front cameras horizontally
        panorama = np.hstack([
            resized_front.get('FRONT_LEFT', np.zeros((ref_height, 400, 3), dtype=np.uint8)),
            resized_front.get('FRONT_CENTER', np.zeros((ref_height, 400, 3), dtype=np.uint8)),
            resized_front.get('FRONT_RIGHT', np.zeros((ref_height, 400, 3), dtype=np.uint8))
        ])
        
        # Resize panorama to target width while maintaining aspect ratio
        h, w = panorama.shape[:2]
        if w > 0:
            scale = width / w
            new_h = int(h * scale)
            panorama = cv2.resize(panorama, (width, new_h))
        
        return panorama
    except Exception as e:
        print(f"  ⚠ Error stitching panorama: {e}")
        return None


def create_thumbnail(panorama, max_width=512):
    """Create thumbnail from panorama."""
    try:
        h, w = panorama.shape[:2]
        if w > 0:
            scale = max_width / w
            new_h = int(h * scale)
            thumbnail = cv2.resize(panorama, (max_width, new_h))
            return thumbnail
        return None
    except Exception as e:
        print(f"  ⚠ Error creating thumbnail: {e}")
        return None


def compress_image_to_bytes(image, quality=75):
    """Compress image to JPEG bytes for database storage."""
    try:
        success, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if success:
            return buffer.tobytes()
        return None
    except Exception as e:
        print(f"  ⚠ Error compressing image: {e}")
        return None


# ============================================================================
# THRESHOLD MANAGEMENT
# ============================================================================
def load_or_calculate_thresholds(filename, force_recalculate=False):
    """
    Load thresholds from file or calculate adaptively from dataset.
    
    Args:
        filename: Path to tfrecord file
        force_recalculate: Force recalculation even if file exists
    
    Returns:
        Dictionary of thresholds
    """
    # Try to load from file
    if os.path.exists(THRESHOLD_FILE) and not force_recalculate:
        try:
            with open(THRESHOLD_FILE, 'r') as f:
                thresholds = json.load(f)
            print(f"✓ Loaded saved thresholds from {THRESHOLD_FILE}")
            return thresholds
        except Exception as e:
            print(f"⚠ Could not load thresholds: {e}")
    
    # Calculate adaptively from current file
    print("Calculating adaptive thresholds from dataset...")
    all_accel_x = []
    all_accel_y = []
    all_jerk = []
    
    dataset = tf.data.TFRecordDataset(filename, compression_type='')
    for bytes_example in dataset.as_numpy_iterator():
        data = wod_e2ed_pb2.E2EDFrame()
        data.ParseFromString(bytes_example)
        accel_x = np.array(data.past_states.accel_x)
        accel_y = np.array(data.past_states.accel_y)
        all_accel_x.extend(accel_x)
        all_accel_y.extend(accel_y)
        all_jerk.extend(np.abs(np.diff(accel_x)))
    
    # Calculate percentiles (top 5% are anomalies)
    thresholds = {
        'hard_brake': float(np.percentile(all_accel_x, 5)),      # Lowest 5%
        'lateral': float(np.percentile(np.abs(all_accel_y), 95)),  # Highest 5%
        'jerk': float(np.percentile(all_jerk, 95))                 # Highest 5%
    }
    
    # Save for future use
    try:
        with open(THRESHOLD_FILE, 'w') as f:
            json.dump(thresholds, f, indent=2)
        print(f"✓ Saved thresholds to {THRESHOLD_FILE}")
    except Exception as e:
        print(f"⚠ Could not save thresholds: {e}")
    
    return thresholds

# ============================================================================
# LOAD DATA
# ============================================================================
if len(sys.argv) < 2:
    print("Error: Please provide a filename as an argument.")
    sys.exit(1)

filename = sys.argv[1]
print(f"--- Processing file: {filename} ---")

try:
    dataset = tf.data.TFRecordDataset(filename, compression_type='')
    data_iter = dataset.as_numpy_iterator()
    print("✓ Successfully loaded dataset")
except Exception as e:
    print(f"✗ Error processing file {filename}: {e}")
    sys.exit(1)

# Initialize database
db_conn = init_database(DB_PATH)
print(f"✓ Database initialized: {DB_PATH}")

# ============================================================================
# LOAD THRESHOLDS (ADAPTIVE APPROACH)
# ============================================================================
print("\n--- Threshold Management ---")
THRESHOLDS = load_or_calculate_thresholds(filename, force_recalculate=False)

print(f"\n✓ Active Thresholds:")
print(f"  Hard brake: {THRESHOLDS['hard_brake']:.4f} m/s²")
print(f"  Lateral: {THRESHOLDS['lateral']:.4f} m/s²")
print(f"  Jerk: {THRESHOLDS['jerk']:.4f} m/s³")
print(f"\n  Severity normalization: 0.0 at threshold, 1.0 at 3x threshold\n")

# Reload dataset for processing
dataset = tf.data.TFRecordDataset(filename, compression_type='')
data_iter = dataset.as_numpy_iterator()

# ============================================================================
# PROCESS DATA
# ============================================================================
frame_count = 0
edge_case_count = 0

for bytes_example in data_iter:
    data = wod_e2ed_pb2.E2EDFrame()
    data.ParseFromString(bytes_example)
    frame_count += 1
    
    print(f"\n--- Frame {frame_count} ---")
    
    # Extract PAST motion data
    vel_x = np.array(data.past_states.vel_x)
    vel_y = np.array(data.past_states.vel_y)
    accel_x = np.array(data.past_states.accel_x)
    accel_y = np.array(data.past_states.accel_y)
    
    # Calculate motion metrics
    speed = np.sqrt(vel_x**2 + vel_y**2)
    jerk_x = np.abs(np.diff(accel_x)) if len(accel_x) > 1 else np.array([0])
    jerk_y = np.abs(np.diff(accel_y)) if len(accel_y) > 1 else np.array([0])
    
    # Get intent
    intent_map = {
        0: 'UNKNOWN',
        1: 'GO_STRAIGHT',
        2: 'GO_LEFT',
        3: 'GO_RIGHT'
    }
    intent = intent_map.get(data.intent, 'UNKNOWN')
    
    # Compile motion data
    motion_data = {
        'speed_min': float(speed.min()),
        'speed_max': float(speed.max()),
        'speed_mean': float(speed.mean()),
        'accel_x_min': float(accel_x.min()),
        'accel_x_max': float(accel_x.max()),
        'accel_y_min': float(accel_y.min()),
        'accel_y_max': float(accel_y.max()),
        'jerk_x_max': float(jerk_x.max()),
        'jerk_y_max': float(jerk_y.max())
    }
    
    print(f"Speed range: {motion_data['speed_min']:.2f} - {motion_data['speed_max']:.2f} m/s")
    print(f"Accel X: {motion_data['accel_x_min']:.2f} to {motion_data['accel_x_max']:.2f} m/s²")
    print(f"Accel Y: {motion_data['accel_y_min']:.2f} to {motion_data['accel_y_max']:.2f} m/s²")
    print(f"Intent: {intent}")
    
    # Extract camera images and create panorama thumbnail
    panorama_thumbnail_bytes = None
    try:
        camera_images_dict = {}
        
        # Camera name indices in E2ED proto:
        # 1 = FRONT_LEFT, 2 = FRONT_CENTER, 3 = FRONT_RIGHT
        # Based on tutorial return_front3_cameras() function: order = [2, 1, 3]
        camera_mapping = {
            'FRONT_LEFT': 2,
            'FRONT_CENTER': 1,
            'FRONT_RIGHT': 3
        }
        
        # Extract front 3 camera images using TensorFlow decoder (correct method)
        for camera_name, camera_id in camera_mapping.items():
            for index, image_content in enumerate(data.frame.images):
                if image_content.name == camera_id:
                    try:
                        # Use TensorFlow to decode (matches tutorial approach)
                        image_array = tf.io.decode_image(image_content.image).numpy()
                        if image_array is not None:
                            camera_images_dict[camera_name] = image_array
                    except Exception as decode_err:
                        print(f"    ⚠ Could not decode {camera_name}: {decode_err}")
                    break
        
        # Create stitched panorama if we have images
        if len(camera_images_dict) > 0:
            panorama = stitch_panorama(camera_images_dict, width=4096)
            if panorama is not None:
                # Create thumbnail
                thumbnail = create_thumbnail(panorama, max_width=512)
                if thumbnail is not None:
                    # Compress to bytes for database storage
                    panorama_thumbnail_bytes = compress_image_to_bytes(thumbnail, quality=75)
                    thumbnail_size_kb = len(panorama_thumbnail_bytes) / 1024 if panorama_thumbnail_bytes else 0
                    print(f"  ✓ Panorama thumbnail created: {thumbnail_size_kb:.1f} KB")
    except Exception as e:
        print(f"  ⚠ Could not create panorama thumbnail: {e}")
    
    # STORE ALL FRAME DATA and get the database row ID
    frame_table_id = store_frame_data(
        db_conn,
        frame_id=frame_count,
        file_name=os.path.basename(filename),
        timestamp=data.frame.timestamp_micros,
        motion_data=motion_data,
        intent=intent,
        panorama_thumbnail_bytes=panorama_thumbnail_bytes
    )
    
    if frame_table_id is None:
        print(f"  ✗ Failed to store frame data, skipping edge case detection")
        continue
    
    # DETECT AND FLAG EDGE CASES WITH NORMALIZED SEVERITY
    hard_brake = motion_data['accel_x_min'] < THRESHOLDS['hard_brake']
    high_lateral_accel = motion_data['accel_y_max'] > THRESHOLDS['lateral']
    high_jerk = motion_data['jerk_x_max'] > THRESHOLDS['jerk']
    
    if hard_brake:
        # Calculate normalized severity (0-1 scale)
        severity = calculate_normalized_severity(
            motion_data['accel_x_min'],
            THRESHOLDS['hard_brake'],
            is_negative=True
        )
        reason = f"accel_x={motion_data['accel_x_min']:.3f} < threshold {THRESHOLDS['hard_brake']:.3f}"
        store_edge_case(db_conn, frame_table_id, 'hard_brake', severity, reason)
        print(f"⚠ HARD BRAKE FLAGGED: severity={severity:.2f} (accel={motion_data['accel_x_min']:.3f} m/s²)")
        edge_case_count += 1
    
    if high_lateral_accel:
        # Calculate normalized severity (0-1 scale)
        severity = calculate_normalized_severity(
            motion_data['accel_y_max'],
            THRESHOLDS['lateral'],
            is_negative=False
        )
        reason = f"accel_y={motion_data['accel_y_max']:.3f} > threshold {THRESHOLDS['lateral']:.3f}"
        store_edge_case(db_conn, frame_table_id, 'evasive_maneuver', severity, reason)
        print(f"⚠ EVASIVE MANEUVER FLAGGED: severity={severity:.2f} (accel={motion_data['accel_y_max']:.3f} m/s²)")
        edge_case_count += 1
    
    if high_jerk:
        # Calculate normalized severity (0-1 scale)
        severity = calculate_normalized_severity(
            motion_data['jerk_x_max'],
            THRESHOLDS['jerk'],
            is_negative=False
        )
        reason = f"jerk_x={motion_data['jerk_x_max']:.3f} > threshold {THRESHOLDS['jerk']:.3f}"
        store_edge_case(db_conn, frame_table_id, 'high_jerk', severity, reason)
        print(f"⚠ HIGH JERK FLAGGED: severity={severity:.2f} (jerk={motion_data['jerk_x_max']:.3f} m/s³)")
        edge_case_count += 1

# ============================================================================
# SUMMARY & CLEANUP
# ============================================================================
print(f"\n--- Processing complete: {frame_count} frames processed ---")
print(f"--- Total edge cases flagged: {edge_case_count} ---")

# Query database summary
try:
    cursor = db_conn.cursor()
    
    print("\n--- Frames Table Summary ---")
    cursor.execute('SELECT COUNT(*) FROM frames')
    total_frames = cursor.fetchone()[0]
    print(f"Total frames stored: {total_frames}")
    
    cursor.execute('SELECT intent, COUNT(*) FROM frames GROUP BY intent ORDER BY COUNT(*) DESC')
    for intent, count in cursor.fetchall():
        print(f"  {intent}: {count}")
    
    print("\n--- Edge Cases Table Summary ---")
    cursor.execute('SELECT edge_case_type, COUNT(*) FROM edge_cases GROUP BY edge_case_type')
    edge_results = cursor.fetchall()
    if edge_results:
        for edge_type, count in edge_results:
            print(f"  {edge_type}: {count}")
    else:
        print("  No edge cases flagged")
    
    # Verify severity normalization
    print("\n--- Severity Score Validation ---")
    cursor.execute('SELECT MIN(severity), MAX(severity), AVG(severity) FROM edge_cases')
    sev_stats = cursor.fetchone()
    if sev_stats and sev_stats[0] is not None:
        print(f"  Min severity: {sev_stats[0]:.4f}")
        print(f"  Max severity: {sev_stats[1]:.4f}")
        print(f"  Avg severity: {sev_stats[2]:.4f}")
        if sev_stats[1] > 1.0:
            print("  ⚠ WARNING: Severity scores exceed 1.0! Check normalization.")
        else:
            print("  ✓ All severity scores properly normalized to 0-1 range")
        
    # Calculate statistics for thresholding
    print("\n--- Motion Statistics (for future recalibration) ---")
    cursor.execute('''
        SELECT 
            MIN(accel_x_min) as min_accel_x,
            MAX(speed_max) as max_speed,
            MAX(accel_y_max) as max_accel_y,
            MAX(jerk_x_max) as max_jerk_x
        FROM frames
    ''')
    stats = cursor.fetchone()
    if stats:
        print(f"  Min accel X: {stats[0]:.4f} m/s²")
        print(f"  Max speed: {stats[1]:.4f} m/s ({stats[1] * 3.6:.1f} km/h)")
        print(f"  Max accel Y: {stats[2]:.4f} m/s²")
        print(f"  Max jerk X: {stats[3]:.4f} m/s³")
    
except Exception as e:
    print(f"⚠ Could not retrieve summary: {e}")

db_conn.close()
print(f"\n✓ Database closed: {DB_PATH}")