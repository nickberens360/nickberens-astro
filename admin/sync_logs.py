#!/usr/bin/env python3
"""
Script to sync query logs from the main backend's JSON file to the admin SQLite database.
"""
import hashlib
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path


def parse_timestamp(timestamp_str):
    """Parse timestamp from various formats."""
    try:
        # Handle ISO format with microseconds
        if "." in timestamp_str and timestamp_str.endswith("Z"):
            return datetime.fromisoformat(timestamp_str[:-1])
        elif "." in timestamp_str:
            return datetime.fromisoformat(timestamp_str)
        else:
            return datetime.fromisoformat(timestamp_str)
    except ValueError:
        # Fallback to current time if parsing fails
        return datetime.now()


def generate_session_id(client_ip, timestamp):
    """Generate a consistent session ID based on IP and time."""
    # Use a time window of 1 hour for session grouping
    hour_window = timestamp.replace(minute=0, second=0, microsecond=0)
    session_key = f"{client_ip}_{hour_window.isoformat()}"
    return hashlib.md5(session_key.encode()).hexdigest()[:16]


def sync_json_to_sqlite():
    """Sync JSON query logs to SQLite database."""
    # Paths
    json_log_file = Path(os.environ.get("QUERY_LOG_JSON_PATH", "backend/logs/query_logs.json"))
    sqlite_db_file = Path(os.environ.get("RAG_MONITOR_DB_PATH", "admin/rag_monitoring.db"))

    if not json_log_file.exists():
        print(f"JSON log file not found: {json_log_file}")
        return False

    print(f"Syncing logs from {json_log_file} to {sqlite_db_file}")

    # Connect to SQLite database
    conn = sqlite3.connect(sqlite_db_file)
    cursor = conn.cursor()

    # Add location columns if they don't exist
    try:
        cursor.execute("ALTER TABLE query_logs ADD COLUMN client_ip TEXT")
        print("Added client_ip column")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE query_logs ADD COLUMN location_city TEXT")
        print("Added location_city column")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE query_logs ADD COLUMN location_region TEXT")
        print("Added location_region column")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE query_logs ADD COLUMN location_country TEXT")
        print("Added location_country column")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE query_logs ADD COLUMN location_country_code TEXT")
        print("Added location_country_code column")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Get the latest timestamp from SQLite to avoid duplicates
    cursor.execute("SELECT MAX(timestamp) FROM query_logs")
    result = cursor.fetchone()
    last_sync_time = None
    if result[0]:
        last_sync_time = datetime.fromisoformat(result[0])
        print(f"Last synced entry: {last_sync_time}")

    # Process JSON log entries
    processed_count = 0
    skipped_count = 0

    with open(json_log_file, "r") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue

            try:
                entry = json.loads(line.strip())
                timestamp = parse_timestamp(entry.get("timestamp", ""))

                # Skip if already processed
                if last_sync_time and timestamp <= last_sync_time:
                    skipped_count += 1
                    continue

                # Generate session ID
                session_id = generate_session_id(entry.get("client_ip", "unknown"), timestamp)

                # Extract data with defaults
                user_query = entry.get("question", "")
                system_response = entry.get("response", "")
                response_time_ms = (entry.get("response_time") or 0) * 1000  # Convert to ms
                llm_provider = (
                    "anthropic" if entry.get("model_used") == "claude" else entry.get("model_used", "unknown")
                )
                llm_model = entry.get("model_used", "unknown")

                # Handle location data
                client_ip = entry.get("client_ip", "")
                location = entry.get("location", {})
                location_city = location.get("city", "")
                location_region = location.get("region", "")
                location_country = location.get("country_name", "")
                location_country_code = location.get("country_code", "")

                # Handle metadata
                metadata = entry.get("metadata", {})
                vector_search_score = metadata.get("retrieval_score", 0.0)
                sources_used = json.dumps(metadata.get("sources", []))
                follow_up_questions = json.dumps(metadata.get("followup_questions", []))
                cache_hit = metadata.get("cache_hit", False)

                # Error handling
                error_occurred = entry.get("error") is not None
                error_message = str(entry.get("error", "")) if error_occurred else None

                # Insert into SQLite
                cursor.execute(
                    """
                    INSERT INTO query_logs (
                        session_id, user_query, system_response, response_time_ms,
                        llm_provider, llm_model, vector_search_score, sources_used,
                        follow_up_questions, cache_hit, error_occurred, error_message,
                        client_ip, location_city, location_region, location_country, location_country_code,
                        timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        session_id,
                        user_query,
                        system_response,
                        response_time_ms,
                        llm_provider,
                        llm_model,
                        vector_search_score,
                        sources_used,
                        follow_up_questions,
                        cache_hit,
                        error_occurred,
                        error_message,
                        client_ip,
                        location_city,
                        location_region,
                        location_country,
                        location_country_code,
                        timestamp.isoformat(),
                    ),
                )

                processed_count += 1

                if processed_count % 100 == 0:
                    print(f"Processed {processed_count} entries...")

            except json.JSONDecodeError as e:
                print(f"JSON decode error on line {line_num}: {e}")
                continue
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
                continue

    # Commit changes
    conn.commit()
    conn.close()

    print(f"Sync completed:")
    print(f"  - Processed: {processed_count} new entries")
    print(f"  - Skipped: {skipped_count} existing entries")

    return processed_count > 0


if __name__ == "__main__":
    success = sync_json_to_sqlite()
    sys.exit(0 if success else 1)
