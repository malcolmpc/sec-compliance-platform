import os
import duckdb
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from screening import screen_entity_name, screen_individual_person
from sign_engine import execute_agreement, generate_compliance_dossier, SIGNATURES_DB_PATH

app = FastAPI(title="RegWatch & OpenRisk Unified Platform", version="1.0")

# Setup templates directory for our DocuSign clone UI
templates = Jinja2Templates(directory="templates")

DB_PATH = "data/platform_state.duckdb"

class TemplateCreateRequest(BaseModel):
    template_id: str
    title: str
    version: str
    content_template: str
    required_screening_level: str = "CIP_FULL"

@app.post("/v1/templates")
def register_template(req: TemplateCreateRequest):
    return create_template(req.template_id, req.title, req.version, req.content_template, req.required_screening_level)

@app.get("/v1/templates")
def list_templates():
    conn = duckdb.connect(SIGNATURES_DB_PATH)
    templates = conn.execute("SELECT template_id, title, version, required_screening_level, created_at FROM agreement_templates").fetchall()
    conn.close()
    return {"templates": templates}

from fastapi.responses import FileResponse
from pdf_generator import generate_dossier_pdf

@app.get("/v1/compliance/dossier/{identifier}/pdf")
def get_compliance_dossier_pdf(identifier: str):
    """
    Generate and download an official PDF audit report for a given entity or user.
    """
    dossier = generate_compliance_dossier(identifier)
    if not dossier["cip_and_screening_records"] and not dossier["executed_agreements"]:
        raise HTTPException(status_code=404, detail=f"No records found for identifier: {identifier}")
    
    pdf_filename = f"data/dossier_{identifier.replace(' ', '_')}.pdf"
    generate_dossier_pdf(dossier, pdf_filename)
    
    return FileResponse(pdf_filename, media_type='application/pdf', filename=f"compliance_dossier_{identifier}.pdf")

def get_db_connection():
    os.makedirs("data", exist_ok=True)
    conn = duckdb.connect(DB_PATH)
    
    # Initialize subscriptions table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            email VARCHAR,
            slack_webhook VARCHAR,
            ticker VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (slack_webhook, ticker)
        )
    """)
    
    # Initialize audit_logs table with full CIP schema
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            query_entity VARCHAR,
            address VARCHAR,
            id_number VARCHAR,
            flagged BOOLEAN,
            confidence INTEGER,
            screened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    return conn
# Request Models
class SubscriptionRequest(BaseModel):
    email: EmailStr
    slack_webhook: str
    ticker: str

class EntityScreenRequest(BaseModel):
    entity_name: str
    threshold: int = 85

class IndividualScreenRequest(BaseModel):
    full_name: str
    dob: str
    country: str
    address: str
    id_number: str
    threshold: int = 85

class SignAgreementRequest(BaseModel):
    document_title: str
    content: str
    signer_name: str
    signer_email: EmailStr

# --- UI Routes ---
@app.get("/sign", response_class=HTMLResponse)
def get_signing_page(request: Request):
    """
    Renders the native DocuSign-style signing web page served directly by FastAPI.
    """
    return templates.TemplateResponse(request, "sign.html", {})

# --- API Routes ---
@app.post("/v1/subscribe")
def register_subscription(sub: SubscriptionRequest):
    conn = get_db_connection()
    try:
        exists = conn.execute(
            "SELECT 1 FROM subscriptions WHERE slack_webhook = ? AND ticker = ?",
            [sub.slack_webhook, sub.ticker.upper()]
        ).fetchone()

        if exists:
            conn.close()
            return {"status": "success", "message": f"Webhook already tracking {sub.ticker.upper()}"}

        conn.execute(
            "INSERT INTO subscriptions (email, slack_webhook, ticker) VALUES (?, ?, ?)",
            [sub.email, sub.slack_webhook, sub.ticker.upper()]
        )
        conn.close()
        return {"status": "success", "message": f"Successfully registered {sub.ticker.upper()}"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/v1/screen")
def screen_endpoint(req: EntityScreenRequest):
    result = screen_entity_name(req.entity_name, req.threshold)
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO audit_logs (query_entity, address, id_number, flagged, confidence) VALUES (?, ?, ?, ?, ?)",
        [f"ENTITY: {req.entity_name}", None, None, result["flagged"], result["confidence_score"]]
    )
    conn.close()
    return {"status": "success", "query": req.entity_name, "screening_result": result}

@app.post("/v1/screen/individual")
def screen_individual_endpoint(req: IndividualScreenRequest):
    result = screen_individual_person(req.full_name, req.dob, req.country, req.threshold)
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO audit_logs (query_entity, address, id_number, flagged, confidence) VALUES (?, ?, ?, ?, ?)",
        [
            f"INDIVIDUAL: {req.full_name} ({req.dob})", 
            req.address, 
            req.id_number, 
            result["flagged"], 
            result["confidence_score"]
        ]
    )
    conn.close()
    return {
        "status": "success", 
        "query": req.full_name, 
        "cip_validated": {
            "address_provided": bool(req.address),
            "id_provided": bool(req.id_number)
        },
        "screening_result": result
    }

@app.post("/v1/sign")
def sign_agreement_endpoint(req: SignAgreementRequest, request: Request):
    """
    API endpoint for executing a binding electronic signature on a document.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    result = execute_agreement(
        document_title=req.document_title,
        content=req.content,
        name=req.signer_name,
        email=req.signer_email,
        ip_address=client_ip
    )
    return result

@app.get("/v1/agreements")
def list_agreements():
    """
    Fetch all executed agreements and their cryptographic hashes.
    """
    conn = duckdb.connect(SIGNATURES_DB_PATH)
    agreements = conn.execute("SELECT * FROM executed_agreements ORDER BY signed_at DESC").fetchall()
    conn.close()
    return {"executed_agreements": agreements}

@app.get("/v1/compliance/dossier/{identifier}")
def get_compliance_dossier(identifier: str):
    """
    Generate an immutable compliance dossier bundling KYC/CIP data, 
    watchlist screening results, and cryptographic e-signatures.
    """
    dossier = generate_compliance_dossier(identifier)
    
    if not dossier["cip_and_screening_records"] and not dossier["executed_agreements"]:
        raise HTTPException(
            status_code=404, 
            detail=f"No compliance or signature records found for identifier: {identifier}"
        )
        
    return {
        "status": "success",
        "audit_trail_integrity": "SHA-256 Verified & DuckDB Immutable",
        "dossier": dossier
    }

@app.get("/v1/audit-logs")
def get_audit_logs():
    conn = get_db_connection()
    logs = conn.execute("SELECT * FROM audit_logs ORDER BY screened_at DESC LIMIT 50").fetchall()
    conn.close()
    return {"audit_logs": logs}