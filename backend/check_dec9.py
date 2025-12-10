"""Quick script to check Dec 9 data in database."""
from app.database import SessionLocal
from app.models import Connection, MetricSnapshot, Entity
from sqlalchemy import func
from datetime import date

db = SessionLocal()

# Get your Google connection
conn = db.query(Connection).filter(Connection.provider == 'google').first()
print(f'Connection: {conn.name}')
print(f'Currency: {conn.currency_code}')

# Sum metrics for Dec 9
dec9 = date(2025, 12, 9)
result = db.query(
    func.sum(MetricSnapshot.spend),
    func.sum(MetricSnapshot.conversions),
    func.sum(MetricSnapshot.revenue),
    func.count(MetricSnapshot.id)
).join(Entity).filter(
    Entity.connection_id == conn.id,
    func.date(MetricSnapshot.captured_at) == dec9
).first()

print(f'Dec 9 totals from DB:')
print(f'  Spend: {result[0]}')
print(f'  Conversions: {result[1]}')
print(f'  Revenue: {result[2]}')
print(f'  Snapshot count: {result[3]}')

db.close()
