import os
import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import Alert, NASReport

LINE_TOKEN = os.getenv("LINE_TOKEN", "")
LINE_USER_ID = os.getenv("LINE_USER_ID", "")

CPU_THRESHOLD = float(os.getenv("CPU_THRESHOLD", "90"))
DISK_THRESHOLD = float(os.getenv("DISK_THRESHOLD", "85"))


def send_line(message: str):
    if not LINE_TOKEN or not LINE_USER_ID:
        return
    try:
        requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"},
            json={"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]},
            timeout=10,
        )
    except Exception:
        pass


def already_alerted(db: Session, client_id: int, alert_type: str, within_minutes=60) -> bool:
    since = datetime.now() - timedelta(minutes=within_minutes)
    return db.query(Alert).filter(
        Alert.client_id == client_id,
        Alert.alert_type == alert_type,
        Alert.timestamp >= since,
        Alert.resolved == False,
    ).first() is not None


def check_and_alert(client, data, db: Session):
    alerts = []

    if data.backup_status == "failed":
        if not already_alerted(db, client.id, "backup_fail"):
            alerts.append(("backup_fail", f"⚠️ [{client.name}] 備份失敗！\n{data.backup_details}"))

    if data.disk_usage >= DISK_THRESHOLD:
        if not already_alerted(db, client.id, "disk_full"):
            alerts.append(("disk_full", f"💾 [{client.name}] 硬碟空間不足！使用率 {data.disk_usage:.1f}%"))

    if data.cpu_usage >= CPU_THRESHOLD:
        if not already_alerted(db, client.id, "cpu_high"):
            alerts.append(("cpu_high", f"🔥 [{client.name}] CPU 過高！使用率 {data.cpu_usage:.1f}%"))

    for alert_type, message in alerts:
        db.add(Alert(
            client_id=client.id,
            client_name=client.name,
            alert_type=alert_type,
            message=message,
        ))
        send_line(message)

    db.commit()
