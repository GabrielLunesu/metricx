"""Check latest snapshots for Dec 9."""
from app.database import SessionLocal
from app.models import Connection, MetricSnapshot, Entity
from datetime import date
from sqlalchemy import func

db = SessionLocal()
conn = db.query(Connection).filter(Connection.provider == 'google').first()
print(f"Connection: {conn.name}, Currency: {conn.currency_code}")

dec9 = date(2025, 12, 9)

# Get all unique times for Dec 9
times = db.query(
    MetricSnapshot.captured_at,
    func.count(MetricSnapshot.id).label('count'),
    func.sum(MetricSnapshot.spend).label('total_spend')
).join(Entity).filter(
    Entity.connection_id == conn.id,
    func.date(MetricSnapshot.captured_at) == dec9
).group_by(MetricSnapshot.captured_at).order_by(MetricSnapshot.captured_at).all()

print(f"\nDec 9 snapshot times:")
for t in times:
    print(f"  {t.captured_at} | {t.count} snapshots | total spend: {t.total_spend}")

# Also show total entity count
entity_count = db.query(func.count(Entity.id)).filter(
    Entity.connection_id == conn.id
).scalar()
print(f"\nTotal entities for this connection: {entity_count}")

db.close()
