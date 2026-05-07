from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
import os

from database import get_db, init_db, Client, NASReport, Alert
from alerts import check_and_alert

app = FastAPI(title="NAS Monitor")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup():
    init_db()


# ── 資料模型 ──────────────────────────────────────────────
class ReportIn(BaseModel):
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    backup_status: str        # ok / failed / warning / unknown
    backup_details: Optional[str] = ""


class ClientIn(BaseModel):
    name: str
    nas_type: str             # synology / qnap
    email: Optional[str] = ""


# ── Agent 推送端點 ────────────────────────────────────────
@app.post("/report")
def receive_report(
    data: ReportIn,
    x_api_key: str = Header(...),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.api_key == x_api_key).first()
    if not client:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    report = NASReport(
        client_id=client.id,
        cpu_usage=data.cpu_usage,
        memory_usage=data.memory_usage,
        disk_usage=data.disk_usage,
        backup_status=data.backup_status,
        backup_details=data.backup_details,
    )
    db.add(report)

    client.last_seen = datetime.now()
    client.last_status = data.backup_status
    db.commit()

    check_and_alert(client, data, db)
    return {"status": "ok"}


# ── 管理端點 ─────────────────────────────────────────────
ADMIN_KEY = os.getenv("ADMIN_KEY", "admin123")


def verify_admin(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


@app.get("/clients")
def list_clients(db: Session = Depends(get_db), _=Depends(verify_admin)):
    return db.query(Client).all()


@app.post("/clients")
def add_client(data: ClientIn, db: Session = Depends(get_db), _=Depends(verify_admin)):
    import secrets
    api_key = secrets.token_hex(16)
    client = Client(name=data.name, nas_type=data.nas_type, email=data.email, api_key=api_key)
    db.add(client)
    db.commit()
    return {"name": data.name, "api_key": api_key}


@app.get("/alerts")
def list_alerts(db: Session = Depends(get_db), _=Depends(verify_admin)):
    return db.query(Alert).filter(Alert.resolved == False).order_by(Alert.timestamp.desc()).limit(50).all()


# ── 儀表板 ────────────────────────────────────────────────
@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    clients = db.query(Client).all()
    now = datetime.now()
    status_list = []
    for c in clients:
        offline = c.last_seen is None or (now - c.last_seen) > timedelta(minutes=30)
        status_list.append({
            "name": c.name,
            "nas_type": c.nas_type,
            "last_seen": c.last_seen.strftime("%Y-%m-%d %H:%M") if c.last_seen else "從未回報",
            "status": "offline" if offline else c.last_status,
            "offline": offline,
        })
    unresolved = db.query(Alert).filter(Alert.resolved == False).count()
    return templates.TemplateResponse(request, "dashboard.html", {
        "clients": status_list,
        "unresolved_alerts": unresolved,
        "now": now.strftime("%Y-%m-%d %H:%M"),
    })
