"""
QA System Accuracy Tests

Tests the QA Copilot against known database values to catch:
1. Hallucinated numbers
2. Mismatched timeseries vs summary values
3. Wrong date ranges
4. Tool execution issues

Run with: pytest tests/test_qa_accuracy.py -v
"""

import pytest
import json
import re
from decimal import Decimal
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text
from app.database import SessionLocal
from app.agent.tools import SemanticTools
from app.services.unified_metric_service import UnifiedMetricService


# Test workspace (update for your environment)
TEST_WORKSPACE_ID = "540c956d-b31b-4c3c-8185-29cc49979b25"


class TestTimeseriesMatchesSummary:
    """Verify timeseries data sums to the same value as summary."""

    def setup_method(self):
        self.db = SessionLocal()
        self.tools = SemanticTools(self.db, TEST_WORKSPACE_ID, "test")

    def teardown_method(self):
        self.db.close()

    def test_7d_timeseries_matches_summary(self):
        """7-day timeseries should sum to summary value."""
        result = self.tools.query_metrics(
            metrics=["spend"],
            time_range="7d",
            include_timeseries=True,
            compare_to_previous=False,
        )

        assert result.get("success"), f"Query failed: {result.get('error')}"

        summary_value = result["data"]["summary"]["spend"]["value"]
        timeseries = result["data"]["timeseries"]["spend"]
        timeseries_sum = sum(p["value"] for p in timeseries)

        # Allow small floating point difference
        assert abs(summary_value - timeseries_sum) < 0.01, (
            f"Summary ({summary_value}) != Timeseries sum ({timeseries_sum})"
        )

    def test_30d_timeseries_matches_summary(self):
        """30-day timeseries should sum to summary value."""
        result = self.tools.query_metrics(
            metrics=["spend"],
            time_range="30d",
            include_timeseries=True,
            compare_to_previous=False,
        )

        assert result.get("success"), f"Query failed: {result.get('error')}"

        summary_value = result["data"]["summary"]["spend"]["value"]
        timeseries = result["data"]["timeseries"]["spend"]
        timeseries_sum = sum(p["value"] for p in timeseries)

        assert abs(summary_value - timeseries_sum) < 0.01, (
            f"Summary ({summary_value}) != Timeseries sum ({timeseries_sum})"
        )

    def test_comparison_timeseries_matches_summary(self):
        """Comparison query: both periods should match their summaries."""
        result = self.tools.query_metrics(
            metrics=["spend"],
            time_range="7d",
            include_timeseries=True,
            compare_to_previous=True,
        )

        assert result.get("success"), f"Query failed: {result.get('error')}"

        # Current period
        summary_value = result["data"]["summary"]["spend"]["value"]
        timeseries = result["data"]["timeseries"]["spend"]
        timeseries_sum = sum(p["value"] for p in timeseries)

        assert abs(summary_value - timeseries_sum) < 0.01, (
            f"Current: Summary ({summary_value}) != Timeseries sum ({timeseries_sum})"
        )

        # Previous period
        previous_value = result["data"]["summary"]["spend"]["previous"]
        previous_timeseries = result["data"]["timeseries"].get("spend_previous", [])
        previous_sum = sum(p["value"] for p in previous_timeseries)

        assert abs(previous_value - previous_sum) < 0.01, (
            f"Previous: Summary ({previous_value}) != Timeseries sum ({previous_sum})"
        )


class TestDatabaseConsistency:
    """Verify query_metrics matches raw database queries."""

    def setup_method(self):
        self.db = SessionLocal()
        self.tools = SemanticTools(self.db, TEST_WORKSPACE_ID, "test")

    def teardown_method(self):
        self.db.close()

    def test_spend_matches_database(self):
        """query_metrics spend should match raw SQL with latest-snapshot-per-day."""
        # Get from query_metrics
        result = self.tools.query_metrics(
            metrics=["spend"], time_range="7d", include_timeseries=False
        )

        assert result.get("success")
        tool_spend = result["data"]["summary"]["spend"]["value"]

        # Get from raw SQL (correct method: latest snapshot per entity per day)
        today = date.today()
        end_date = today
        start_date = today - timedelta(days=6)

        raw_result = self.db.execute(
            text("""
            WITH latest_snapshots AS (
                SELECT DISTINCT ON (ms.entity_id, ms.metrics_date)
                    ms.entity_id,
                    ms.metrics_date,
                    ms.spend
                FROM metric_snapshots ms
                JOIN entities e ON ms.entity_id = e.id
                WHERE e.workspace_id = :ws_id
                AND e.level = 'campaign'
                AND ms.metrics_date BETWEEN :start_date AND :end_date
                ORDER BY ms.entity_id, ms.metrics_date, ms.captured_at DESC
            )
            SELECT COALESCE(SUM(spend), 0) as total_spend
            FROM latest_snapshots
        """),
            {
                "ws_id": TEST_WORKSPACE_ID,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        db_spend = float(raw_result.scalar())

        assert abs(tool_spend - db_spend) < 0.01, (
            f"Tool ({tool_spend}) != Database ({db_spend})"
        )


class TestNoSnapshotDuplication:
    """Ensure we're not summing duplicate snapshots."""

    def setup_method(self):
        self.db = SessionLocal()

    def teardown_method(self):
        self.db.close()

    def test_snapshots_per_entity_per_day(self):
        """Check how many snapshots exist per entity per day."""
        result = self.db.execute(
            text("""
            SELECT 
                ms.entity_id,
                ms.metrics_date,
                COUNT(*) as snapshot_count
            FROM metric_snapshots ms
            JOIN entities e ON ms.entity_id = e.id
            WHERE e.workspace_id = :ws_id
            AND ms.metrics_date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY ms.entity_id, ms.metrics_date
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            LIMIT 5
        """),
            {"ws_id": TEST_WORKSPACE_ID},
        )

        rows = result.fetchall()
        if rows:
            print(f"\nFound {len(rows)} entity-days with multiple snapshots")
            print("This is expected - we use latest snapshot per day")
            for row in rows:
                print(f"  Entity {row[0][:8]}..., Date {row[1]}: {row[2]} snapshots")


class TestMetricCalculations:
    """Verify derived metrics are calculated correctly."""

    def setup_method(self):
        self.db = SessionLocal()
        self.tools = SemanticTools(self.db, TEST_WORKSPACE_ID, "test")

    def teardown_method(self):
        self.db.close()

    def test_roas_calculation(self):
        """ROAS should equal revenue / spend."""
        result = self.tools.query_metrics(
            metrics=["spend", "revenue", "roas"], time_range="7d"
        )

        assert result.get("success")

        spend = float(result["data"]["summary"]["spend"]["value"])
        revenue = float(result["data"]["summary"]["revenue"]["value"])
        roas = float(result["data"]["summary"]["roas"]["value"])

        if spend > 0:
            expected_roas = revenue / spend
            assert abs(roas - expected_roas) < 0.01, (
                f"ROAS ({roas}) != revenue/spend ({expected_roas})"
            )

    def test_cpc_calculation(self):
        """CPC should equal spend / clicks."""
        result = self.tools.query_metrics(
            metrics=["spend", "clicks", "cpc"], time_range="7d"
        )

        assert result.get("success")

        spend = float(result["data"]["summary"]["spend"]["value"])
        clicks = float(result["data"]["summary"]["clicks"]["value"])
        cpc = float(result["data"]["summary"]["cpc"]["value"])

        if clicks > 0:
            expected_cpc = spend / clicks
            assert abs(cpc - expected_cpc) < 0.01, (
                f"CPC ({cpc}) != spend/clicks ({expected_cpc})"
            )


class TestDeltaCalculations:
    """Verify period-over-period delta calculations."""

    def setup_method(self):
        self.db = SessionLocal()
        self.tools = SemanticTools(self.db, TEST_WORKSPACE_ID, "test")

    def teardown_method(self):
        self.db.close()

    def test_delta_pct_calculation(self):
        """delta_pct should equal (current - previous) / previous."""
        result = self.tools.query_metrics(
            metrics=["spend"], time_range="7d", compare_to_previous=True
        )

        assert result.get("success")

        current = result["data"]["summary"]["spend"]["value"]
        previous = result["data"]["summary"]["spend"]["previous"]
        delta_pct = result["data"]["summary"]["spend"]["delta_pct"]

        if previous > 0:
            expected_delta = (current - previous) / previous
            assert abs(delta_pct - expected_delta) < 0.0001, (
                f"delta_pct ({delta_pct}) != expected ({expected_delta})"
            )


class TestVisualBuilding:
    """Test that visuals are built correctly from data."""

    def setup_method(self):
        self.db = SessionLocal()
        self.tools = SemanticTools(self.db, TEST_WORKSPACE_ID, "test")

    def teardown_method(self):
        self.db.close()

    def test_timeseries_generates_chart(self):
        """Timeseries query should produce a visual spec."""
        from app.agent.nodes import _build_visuals_from_data

        result = self.tools.query_metrics(
            metrics=["spend"], time_range="7d", include_timeseries=True
        )

        assert result.get("success")

        visuals = _build_visuals_from_data(
            result["data"], {"metrics": ["spend"], "include_timeseries": True}
        )

        assert visuals is not None, "No visuals generated"
        assert len(visuals.get("viz_specs", [])) > 0, "No viz_specs in visuals"

        # Check chart structure
        chart = visuals["viz_specs"][0]
        assert "type" in chart, "Chart missing type"
        assert "series" in chart, "Chart missing series"
        assert len(chart["series"]) > 0, "Chart has no series data"

    def test_comparison_generates_line_chart(self):
        """Comparison query should produce overlaid line chart."""
        from app.agent.nodes import _build_visuals_from_data

        result = self.tools.query_metrics(
            metrics=["spend"],
            time_range="7d",
            include_timeseries=True,
            compare_to_previous=True,
        )

        assert result.get("success")

        visuals = _build_visuals_from_data(
            result["data"],
            {
                "metrics": ["spend"],
                "include_timeseries": True,
                "compare_to_previous": True,
            },
        )

        assert visuals is not None

        # Should have a comparison chart
        comparison_charts = [
            c for c in visuals.get("viz_specs", []) if c.get("isComparison")
        ]
        assert len(comparison_charts) > 0, "No comparison chart generated"

        # Comparison chart should have 2 series
        chart = comparison_charts[0]
        assert len(chart["series"]) == 2, (
            f"Expected 2 series, got {len(chart['series'])}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
