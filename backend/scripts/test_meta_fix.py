"""Quick local test to verify the act_ prefix fix.

WHAT: Connects to the real DB, finds the Neyli Shop Meta connection,
      and tests the Meta API call with/without the act_ prefix.

USAGE:
    cd backend && python scripts/test_meta_fix.py

SAFE: This is read-only — only fetches insights, never writes.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models import Connection, ProviderEnum
from app.security import decrypt_secret
from app.services.meta_ads_client import (
    MetaAdsClient,
    MetaAdsClientError,
    MetaAdsValidationError,
    ensure_act_prefix,
)
from datetime import date, timedelta


def main():
    db = SessionLocal()

    print("=" * 60)
    print("META ADS FIX VERIFICATION")
    print("=" * 60)

    # Step 1: Find Meta connection (prefer one with encrypted token and numeric ID)
    connections = db.query(Connection).filter(
        Connection.provider == ProviderEnum.meta,
        Connection.status == "active",
    ).all()
    # Pick the first connection that has an encrypted token (real OAuth connection)
    connection = next(
        (c for c in connections if c.token and c.token.access_token_enc),
        connections[0] if connections else None,
    )

    if not connection:
        print("ERROR: No active Meta connection found in DB")
        return

    print(f"\nConnection: {connection.id}")
    print(f"Account:    {connection.external_account_id}")
    print(f"Name:       {connection.name}")

    # Step 2: Get access token
    if connection.token and connection.token.access_token_enc:
        access_token = decrypt_secret(
            connection.token.access_token_enc,
            context=f"meta-connection:{connection.id}",
        )
        print(f"Token:      decrypted OK ({len(access_token)} chars)")
    else:
        access_token = os.getenv("META_ACCESS_TOKEN")
        if not access_token:
            print("ERROR: No access token available")
            return
        print("Token:      from .env")

    raw_id = connection.external_account_id
    fixed_id = ensure_act_prefix(raw_id)

    print(f"\nRaw ID:     {raw_id}")
    print(f"Fixed ID:   {fixed_id}")
    print(f"Has prefix: {raw_id.startswith('act_')}")

    client = MetaAdsClient(access_token=access_token)
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Step 3: Test WITHOUT prefix (reproducing the bug)
    print("\n" + "-" * 60)
    print(f"TEST 1: API call WITHOUT act_ prefix (raw: {raw_id})")
    print("-" * 60)
    try:
        # Bypass the fix by calling the SDK directly
        from facebook_business.adobjects.adaccount import AdAccount
        from facebook_business.adobjects.adsinsights import AdsInsights
        from facebook_business.exceptions import FacebookRequestError

        account = AdAccount(raw_id)  # No prefix — this is the old bug
        insights = account.get_insights(
            fields=[
                AdsInsights.Field.spend,
                AdsInsights.Field.impressions,
            ],
            params={
                "level": "account",
                "time_range": {"since": yesterday.isoformat(), "until": today.isoformat()},
            },
        )
        # Try to iterate (triggers the API call)
        data = [dict(i) for i in insights]
        print(f"UNEXPECTED SUCCESS: Got {len(data)} rows (prefix may not be needed for this account)")
    except FacebookRequestError as e:
        print(f"EXPECTED ERROR: {e.api_error_message()}")
        print(f"Error code:    {e.api_error_code()}")
        print(f"HTTP status:   {e.http_status()}")
        print(">> This confirms the bug — missing act_ prefix causes failure")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

    # Step 4: Test WITH prefix (the fix)
    print("\n" + "-" * 60)
    print(f"TEST 2: API call WITH act_ prefix (fixed: {fixed_id})")
    print("-" * 60)
    try:
        insights = client.get_account_insights(
            ad_account_id=fixed_id,
            level="account",
            start_date=yesterday.isoformat(),
            end_date=today.isoformat(),
            time_increment=1,
        )
        print(f"SUCCESS: Got {len(insights)} insight rows")
        if insights:
            row = insights[0]
            print(f"  Date:        {row.get('date_start')} to {row.get('date_stop')}")
            print(f"  Spend:       ${row.get('spend', '0')}")
            print(f"  Impressions: {row.get('impressions', '0')}")
            print(f"  Clicks:      {row.get('clicks', '0')}")
            print(f"  Currency:    {row.get('account_currency', 'N/A')}")
        else:
            print("  (No data for this date range — but API call succeeded)")
        print("\n>> FIX CONFIRMED — the API call works with the act_ prefix")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        print(">> Something else may be wrong (token expired?)")

    # Step 5: Test campaign-level (what the sync actually uses)
    print("\n" + "-" * 60)
    print(f"TEST 3: Campaign-level insights (what the 15-min sync uses)")
    print("-" * 60)
    try:
        insights = client.get_account_insights(
            ad_account_id=fixed_id,
            level="campaign",
            start_date=yesterday.isoformat(),
            end_date=today.isoformat(),
            time_increment=1,
            fields=[
                "campaign_id", "campaign_name", "spend", "impressions", "clicks",
                "actions", "action_values", "account_currency",
            ],
        )
        print(f"SUCCESS: Got {len(insights)} campaign insight rows")
        for row in insights[:3]:
            print(f"  Campaign: {row.get('campaign_name', 'N/A')[:40]}")
            print(f"    Spend: ${row.get('spend', '0')}  Impressions: {row.get('impressions', '0')}")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)

    db.close()


if __name__ == "__main__":
    main()
