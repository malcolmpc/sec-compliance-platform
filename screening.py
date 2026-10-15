import os
import csv
import requests
import duckdb

OPENSANCTIONS_CSV_URL = "https://data.opensanctions.org/datasets/latest/default/targets.simple.csv"
SANCTIONS_DB_PATH = "data/platform_state.duckdb"

def sync_sanctions_database():
    """
    Downloads and indexes the official OpenSanctions bulk CSV feed 
    into DuckDB for lightning-fast, offline compliance screening.
    """
    os.makedirs("data", exist_ok=True)
    conn = duckdb.connect(SANCTIONS_DB_PATH)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sanctions_catalog (
            id VARCHAR,
            name VARCHAR,
            datasets VARCHAR,
            countries VARCHAR,
            topics VARCHAR
        )
    """)
    
    # Check if catalog is already populated
    count = conn.execute("SELECT COUNT(*) FROM sanctions_catalog").fetchone()[0]
    if count > 0:
        conn.close()
        return  # Already synced
    
    print("Syncing OpenSanctions watchlist database...")
    response = requests.get(OPENSANCTIONS_CSV_URL, stream=True)
    if response.status_code == 200:
        decoded_content = response.content.decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_content)
        
        batch = []
        for row in reader:
            batch.append((
                row.get("id"),
                row.get("name"),
                row.get("datasets"),
                row.get("countries"),
                row.get("topics")
            ))
            if len(batch) >= 1000:
                conn.executemany("INSERT INTO sanctions_catalog VALUES (?, ?, ?, ?, ?)", batch)
                batch = []
        if batch:
            conn.executemany("INSERT INTO sanctions_catalog VALUES (?, ?, ?, ?, ?)", batch)
    conn.close()

def screen_individual_person(full_name: str, dob: str, country: str, threshold: int = 85):
    sync_sanctions_database()
    conn = duckdb.connect(SANCTIONS_DB_PATH)
    
    # Exact or substring match against live global sanctions/PEP database
    match = conn.execute(
        """
        SELECT name, datasets, countries, topics 
        FROM sanctions_catalog 
        WHERE LOWER(name) LIKE LOWER(?) 
        LIMIT 1
        """,
        [f"%{full_name.strip()}%"]
    ).fetchone()
    conn.close()
    
    if match:
        return {
            "flagged": True,
            "confidence_score": 100,
            "matched_name": match[0],
            "datasets": match[1],
            "country": match[2],
            "category": match[3]
        }
    return {
        "flagged": False,
        "confidence_score": 0,
        "matched_name": None,
        "category": "Clear"
    }

def screen_entity_name(entity_name: str, threshold: int = 85):
    return screen_individual_person(entity_name, "", "", threshold)