import hashlib
import os
import duckdb
from datetime import datetime

SIGNATURES_DB_PATH = "data/platform_state.duckdb"

def init_signatures_table():
    conn = duckdb.connect(SIGNATURES_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS executed_agreements (
            agreement_id VARCHAR PRIMARY KEY,
            document_title VARCHAR,
            document_hash VARCHAR,
            signer_name VARCHAR,
            signer_email VARCHAR,
            signer_ip VARCHAR,
            signed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.close()

def hash_document_text(text_content: str) -> str:
    """Generate a tamper-proof SHA-256 hash of the agreement content."""
    return hashlib.sha256(text_content.encode('utf-8')).hexdigest()

def execute_agreement(document_title: str, content: str, name: str, email: str, ip_address: str):
    """
    Records an electronically signed agreement, locking it with a SHA-256 hash.
    """
    init_signatures_table()
    doc_hash = hash_document_text(content)
    agreement_id = f"AGR-{hashlib.md5(f'{email}-{datetime.utcnow()}'.encode()).hexdigest()[:10].upper()}"
    
    conn = duckdb.connect(SIGNATURES_DB_PATH)
    conn.execute(
        """
        INSERT INTO executed_agreements 
        (agreement_id, document_title, document_hash, signer_name, signer_email, signer_ip) 
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [agreement_id, document_title, doc_hash, name, email, ip_address]
    )
    conn.close()
    
    return {
        "status": "success",
        "agreement_id": agreement_id,
        "document_hash": doc_hash,
        "signed_at": datetime.utcnow().isoformat()
    }

def generate_compliance_dossier(identifier: str):
    """
    Compiles a comprehensive compliance dossier linking KYC/CIP audit logs 
    and executed agreements for a given user name, email, or ID number.
    """
    init_signatures_table()
    conn = duckdb.connect(SIGNATURES_DB_PATH)
    
    # 1. Fetch latest KYC/CIP screening audit logs matching the query entity or ID
    screening_records = conn.execute(
        """
        SELECT query_entity, address, id_number, flagged, confidence, screened_at 
        FROM audit_logs 
        WHERE query_entity LIKE ? OR id_number LIKE ?
        ORDER BY screened_at DESC
        """,
        [f"%{identifier}%", f"%{identifier}%"]
    ).fetchall()
    
    # 2. Fetch executed agreements matching the signer name or email
    agreement_records = conn.execute(
        """
        SELECT agreement_id, document_title, document_hash, signer_name, signer_email, signer_ip, signed_at 
        FROM executed_agreements 
        WHERE signer_name LIKE ? OR signer_email LIKE ?
        ORDER BY signed_at DESC
        """,
        [f"%{identifier}%", f"%{identifier}%"]
    ).fetchall()
    
    conn.close()
    
    return {
        "search_identifier": identifier,
        "dossier_generated_at": datetime.utcnow().isoformat(),
        "cip_and_screening_records": [
            {
                "entity": row[0],
                "address": row[1],
                "id_number": row[2] if row[2] else "N/A",
                "flagged": row[3],
                "confidence_score": row[4],
                "screened_at": row[5]
            } for row in screening_records
        ],
        "executed_agreements": [
            {
                "agreement_id": row[0],
                "document_title": row[1],
                "document_hash": row[2],
                "signer_name": row[3],
                "signer_email": row[4],
                "signer_ip": row[5],
                "signed_at": row[6]
            } for row in agreement_records
        ]
    }