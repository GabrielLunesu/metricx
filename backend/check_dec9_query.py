"""Test the exact query the dashboard uses."""
from app.database import SessionLocal
from sqlalchemy import text
from datetime import date

db = SessionLocal()

# Get workspace_id
from app.models import Connection
conn = db.query(Connection).filter(Connection.provider == 'google').first()
workspace_id = str(conn.workspace_id)

dec9 = date(2025, 12, 9)

# This is the exact query from dashboard.py
query = text("""
    SELECT
        COALESCE(SUM(spend), 0) as spend,
        COALESCE(SUM(revenue), 0) as revenue,
        COALESCE(SUM(conversions), 0) as conversions
    FROM (
        SELECT DISTINCT ON (entity_id, date_trunc('day', captured_at))
            entity_id,
            spend,
            revenue,
            conversions
        FROM metric_snapshots
        WHERE entity_id IN (SELECT id FROM entities WHERE workspace_id = :workspace_id)
          AND date_trunc('day', captured_at) >= :start_date
          AND date_trunc('day', captured_at) <= :end_date
        ORDER BY entity_id, date_trunc('day', captured_at), captured_at DESC
    ) latest_snapshots
""")

result = db.execute(query, {
    "workspace_id": workspace_id,
    "start_date": dec9,
    "end_date": dec9
}).first()

print(f"Dashboard query result for Dec 9:")
print(f"  Spend: {result[0]}")
print(f"  Revenue: {result[1]}")
print(f"  Conversions: {result[2]}")

# Also check what DISTINCT ON returns
detail_query = text("""
    SELECT DISTINCT ON (entity_id, date_trunc('day', captured_at))
        entity_id,
        captured_at,
        spend,
        revenue,
        conversions
    FROM metric_snapshots
    WHERE entity_id IN (SELECT id FROM entities WHERE workspace_id = :workspace_id)
      AND date_trunc('day', captured_at) = :target_date
    ORDER BY entity_id, date_trunc('day', captured_at), captured_at DESC
""")

print(f"\nLatest snapshot per entity for Dec 9:")
rows = db.execute(detail_query, {
    "workspace_id": workspace_id,
    "target_date": dec9
}).fetchall()

for r in rows:
    print(f"  {r.captured_at} | spend={r.spend} | conv={r.conversions} | rev={r.revenue}")

db.close()
