"""Check Dec 9 snapshots in detail."""
from app.database import SessionLocal
from app.models import Connection, MetricSnapshot, Entity
from datetime import date

db = SessionLocal()

conn = db.query(Connection).filter(Connection.provider == 'google').first()

dec9 = date(2025, 12, 9)
snapshots = db.query(
    MetricSnapshot.captured_at,
    MetricSnapshot.spend,
    MetricSnapshot.conversions,
    MetricSnapshot.revenue,
    Entity.name,
    Entity.level
).join(Entity).filter(
    Entity.connection_id == conn.id,
    db.query(MetricSnapshot).filter(
        MetricSnapshot.captured_at >= f'{dec9} 00:00:00',
        MetricSnapshot.captured_at < f'{dec9} 23:59:59'
    ).exists()
).filter(
    MetricSnapshot.captured_at >= f'{dec9} 00:00:00',
    MetricSnapshot.captured_at <= f'{dec9} 23:59:59'
).order_by(MetricSnapshot.captured_at).all()

print(f"Found {len(snapshots)} snapshots for Dec 9:\n")
for s in snapshots:
    print(f"{s.captured_at} | {s.level} | {s.name[:30]:<30} | spend={s.spend} conv={s.conversions}")

db.close()
