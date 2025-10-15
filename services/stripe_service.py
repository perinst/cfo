from typing import Dict, List, Optional
import os
from datetime import datetime

import stripe

from config.database import get_db
from supabase import Client


class StripeService:
    """
    Lightweight Stripe integration for syncing transactions into Supabase 'transactions'.
    - Fetches charges, balance transactions, payouts.
    - Normalizes to our transaction schema.
    - Links to organization via provided org_id and to projects via Stripe metadata mapping.
    """

    def __init__(self, api_key: Optional[str] = None):
        api_key = (
            api_key or os.getenv("STRIPE_API_KEY") or os.getenv("STRIPE_SECRET_KEY")
        )
        if not api_key:
            raise ValueError("Missing STRIPE_API_KEY/STRIPE_SECRET_KEY in environment")
        stripe.api_key = api_key
        self.db: Client = get_db()

    # ------------- Public sync API -------------
    def sync_recent(self, organization_id: str, days: int = 7) -> Dict:
        """Fetch recent charges and payouts and upsert into transactions."""
        try:
            now = int(datetime.utcnow().timestamp())
            since = now - days * 24 * 3600

            charges = stripe.Charge.list(created={"gte": since}, limit=100)
            payouts = stripe.Payout.list(created={"gte": since}, limit=100)

            count = 0
            for ch in charges.auto_paging_iter():
                tx = self._charge_to_tx(ch, organization_id)
                if tx:
                    self._upsert_transaction(tx)
                    count += 1

            for po in payouts.auto_paging_iter():
                tx = self._payout_to_tx(po, organization_id)
                if tx:
                    self._upsert_transaction(tx)
                    count += 1

            return {"success": True, "synced": count}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------- Normalizers -------------
    def _charge_to_tx(self, ch: stripe.Charge, organization_id: str) -> Optional[Dict]:
        try:
            amount = (ch.amount or 0) / 100.0
            currency = ch.currency.upper() if ch.currency else "USD"
            status = ch.status or "succeeded"
            category = "income" if status == "succeeded" else "pending"
            project_id = None
            # Try derive project from metadata
            meta = getattr(ch, "metadata", {}) or {}
            project_id = meta.get("project_id") or meta.get("project")
            desc = ch.description or "Stripe charge"
            merchant = (
                ch.payment_method_details
                and ch.payment_method_details.get("card", {}).get("brand")
            ) or "Stripe"
            tx_date = datetime.fromtimestamp(ch.created).date().isoformat()

            return {
                "transaction_id": ch.id,
                "amount": amount,
                "date": tx_date,
                "category": category,
                "merchant": merchant,
                "employee_id": None,
                "fraud_flag": 1 if getattr(ch, "fraud_details", None) else 0,
                "description": desc,
                "payment_method": (
                    "card" if getattr(ch, "payment_method_details", None) else None
                ),
                "currency": currency,
                "status": status,
                "approval_required": 0,
                "organization_id": organization_id,
                "created_by": None,
                "project_id": project_id,
            }
        except Exception:
            return None

    def _payout_to_tx(self, po: stripe.Payout, organization_id: str) -> Optional[Dict]:
        try:
            amount = (po.amount or 0) / 100.0
            currency = po.currency.upper() if po.currency else "USD"
            status = po.status or "paid"
            category = "payout"
            tx_date = datetime.fromtimestamp(po.created).date().isoformat()
            return {
                "transaction_id": po.id,
                "amount": amount,
                "date": tx_date,
                "category": category,
                "merchant": "Stripe",
                "employee_id": None,
                "fraud_flag": 0,
                "description": "Stripe payout",
                "payment_method": "bank",
                "currency": currency,
                "status": status,
                "approval_required": 0,
                "organization_id": organization_id,
                "created_by": None,
                "project_id": None,
            }
        except Exception:
            return None

    # ------------- Storage helpers -------------
    def _upsert_transaction(self, tx: Dict) -> None:
        # Ensure transactions table has columns; insert or update by transaction_id
        # Add project_id column support dynamically if exists in table
        data = tx.copy()
        # Some installations may not yet have project_id column in transactions; try insert with it, fallback without
        try:
            self.db.table("transactions").upsert(
                data, on_conflict="transaction_id"
            ).execute()
        except Exception:
            data.pop("project_id", None)
            self.db.table("transactions").upsert(
                data, on_conflict="transaction_id"
            ).execute()
