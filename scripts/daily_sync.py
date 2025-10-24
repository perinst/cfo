"""
Run daily to sync recent Stripe transactions. Intended to be scheduled via Windows Task Scheduler or cron.
Requires STRIPE_API_KEY and Supabase env vars.
"""

import os
from datetime import datetime
from config.enviroment import get_config
from services.stripe_service import StripeService


# def main():
# org_id = get_config("SYNC_ORGANIZATION_ID")
# if not org_id:
#     raise SystemExit("SYNC_ORGANIZATION_ID must be set")
# svc = StripeService()
# res = svc.sync_recent(org_id, days=int(get_config("SYNC_DAYS", "1")))
# if res.get("success"):
#     print(
#         f"[{datetime.utcnow().isoformat()}] Synced {res.get('synced',0)} transactions"
#     )
# else:
#     print(f"[{datetime.utcnow().isoformat()}] Sync error: {res.get('error')}")
