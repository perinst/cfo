from typing import Dict, List, Optional, Tuple
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
        api_key = api_key or os.getenv("STRIPE_API_KEY")
        if not api_key:
            raise ValueError("Missing STRIPE_API_KEY/STRIPE_SECRET_KEY in environment")
        stripe.api_key = api_key
        self.db: Client = get_db()
        # optional feature flags
        self.enabled = os.getenv("STRIPE_ENABLED", "1") not in {"0", "false", "False"}
        self.dry_run = os.getenv("STRIPE_DRY_RUN", "0") in {"1", "true", "True"}

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

    # ------------- Disbursement (Connect) API -------------
    def is_account_payout_ready(self, account_id: str) -> Tuple[bool, Optional[str]]:
        """Check if a connected account can receive payouts (KYC/AML, requirements)."""
        try:
            acct = stripe.Account.retrieve(account_id)
            if getattr(acct, "deleted", False):
                return False, "Stripe account deleted"
            if not acct.get("payouts_enabled", False):
                reason = None
                reqs = acct.get("requirements") or {}
                if reqs.get("disabled_reason"):
                    reason = reqs.get("disabled_reason")
                return False, reason or "Payouts not enabled"
            return True, None
        except Exception as e:
            return False, str(e)

    def transfer_and_payout(
        self,
        *,
        organization_id: str,
        to_account_id: str,
        amount_usd: float,
        currency: str = "USD",
        project_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        created_by: Optional[str] = None,
        proposal_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict:
        """
        Move funds from platform balance to a connected account (transfer),
        then initiate a payout from the connected account to their external bank.

        Returns { success, transfer_id, payout_id, status, message }
        Also creates a 'transactions' row with transaction_id=payout_id for webhook reconciliation.
        """
        try:
            if not self.enabled:
                return {
                    "success": False,
                    "error": "Stripe disabled via STRIPE_ENABLED=0",
                }

            # KYC/AML gate
            ready, reason = self.is_account_payout_ready(to_account_id)
            if not ready:
                return {
                    "success": False,
                    "error": f"Account not payout-ready: {reason}",
                }

            # normalize currency/amount
            currency = (currency or "USD").lower()
            amount_cents = int(round((amount_usd or 0.0) * 100))
            if amount_cents <= 0:
                return {"success": False, "error": "Amount must be > 0"}

            meta = {
                "organization_id": str(organization_id),
                "project_id": str(project_id) if project_id else None,
                "employee_id": str(employee_id) if employee_id else None,
                "proposal_id": str(proposal_id) if proposal_id else None,
            }

            # Perform transfer to connected account
            transfer_kwargs = {
                "amount": amount_cents,
                "currency": currency,
                "destination": to_account_id,
                "metadata": {k: v for k, v in meta.items() if v is not None},
            }
            headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None

            if self.dry_run:
                transfer_id = f"tr_test_{datetime.utcnow().timestamp()}"
            else:
                tr = stripe.Transfer.create(
                    **transfer_kwargs, idempotency_key=idempotency_key
                )
                transfer_id = tr.id

            # Create payout from connected account to their external account
            payout_kwargs = {
                "amount": amount_cents,
                "currency": currency,
                "metadata": {k: v for k, v in meta.items() if v is not None},
            }
            if self.dry_run:
                payout_id = f"po_test_{datetime.utcnow().timestamp()}"
                payout_status = "pending"
            else:
                po = stripe.Payout.create(
                    **payout_kwargs,
                    stripe_account=to_account_id,
                    idempotency_key=idempotency_key,
                )
                payout_id = po.id
                payout_status = po.status

            # Record the payout as a transaction for reconciliation (webhook will update status)
            tx_row = {
                "transaction_id": payout_id,
                "amount": amount_cents / 100.0,
                "date": datetime.utcnow().date().isoformat(),
                "category": "payout",
                "merchant": "Stripe",
                "employee_id": employee_id,
                "fraud_flag": 0,
                "description": f"Payout for proposal {proposal_id or ''} (transfer {transfer_id})".strip(),
                "payment_method": "bank",
                "currency": currency.upper(),
                "status": payout_status or "pending",
                "approval_required": 0,
                "organization_id": organization_id,
                "created_by": created_by,
                "project_id": project_id,
            }
            try:
                self.db.table("transactions").upsert(
                    tx_row, on_conflict="transaction_id"
                ).execute()
            except Exception:
                # Fallback without project_id if schema missing
                data2 = tx_row.copy()
                data2.pop("project_id", None)
                self.db.table("transactions").upsert(
                    data2, on_conflict="transaction_id"
                ).execute()

            return {
                "success": True,
                "transfer_id": transfer_id,
                "payout_id": payout_id,
                "status": payout_status,
            }
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
