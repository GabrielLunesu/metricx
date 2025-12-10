"""Check snapshot counts per day."""
from app.database import SessionLocal
from app.models import Connection, MetricSnapshot, Entity
from datetime import date
from sqlalchemy import func

db = SessionLocal()
conn = db.query(Connection).filter(Connection.provider == 'google').first()

for d in [date(2025, 12, 8), date(2025, 12, 9), date(2025, 12, 10)]:
    count = db.query(func.count(MetricSnapshot.id)).join(Entity).filter(
        Entity.connection_id == conn.id,
        func.date(MetricSnapshot.captured_at) == d
    ).scalar()
    print(f'{d}: {count} snapshots')

db.close()
