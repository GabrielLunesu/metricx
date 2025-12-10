"""Check Dec 8 snapshot times."""
from app.database import SessionLocal
from app.models import Connection, MetricSnapshot, Entity
from datetime import date

db = SessionLocal()
conn = db.query(Connection).filter(Connection.provider == 'google').first()

dec8 = date(2025, 12, 8)
snapshots = db.query(
    MetricSnapshot.captured_at,
    MetricSnapshot.spend,
    Entity.name
).join(Entity).filter(
    Entity.connection_id == conn.id,
    MetricSnapshot.captured_at >= f'{dec8} 00:00:00',
    MetricSnapshot.captured_at <= f'{dec8} 23:59:59'
).order_by(MetricSnapshot.captured_at).all()

print(f"Dec 8 snapshots:")
for s in snapshots:
    print(f"  {s.captured_at} | {s.name[:30]} | spend={s.spend}")

db.close()
