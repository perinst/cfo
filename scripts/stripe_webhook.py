import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import stripe
from config.database import get_db

app = FastAPI()

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
stripe.api_key = os.getenv("STRIPE_API_KEY") or os.getenv("STRIPE_SECRET_KEY")


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    if STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload=payload, sig_header=sig_header, secret=STRIPE_WEBHOOK_SECRET
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Webhook signature error: {e}")
    else:
        event = await request.json()

    db = get_db()
    evt_type = event.get("type")
    data = event.get("data", {}).get("object", {})

    try:
        if evt_type == "payment_intent.succeeded":
            # Update transaction status to succeeded by matching charge/intent id if stored
            intent_id = data.get("id")
            if intent_id:
                db.table("transactions").update({"status": "succeeded"}).eq(
                    "transaction_id", intent_id
                ).execute()
        elif evt_type == "charge.succeeded":
            charge_id = data.get("id")
            if charge_id:
                db.table("transactions").update({"status": "succeeded"}).eq(
                    "transaction_id", charge_id
                ).execute()
        elif evt_type == "charge.refunded":
            charge_id = data.get("id")
            if charge_id:
                db.table("transactions").update({"status": "refunded"}).eq(
                    "transaction_id", charge_id
                ).execute()
        elif evt_type == "payout.paid":
            payout_id = data.get("id")
            if payout_id:
                # Mark transaction paid
                db.table("transactions").update({"status": "paid"}).eq(
                    "transaction_id", payout_id
                ).execute()
                # If there is a proposal link in metadata, update proposal payout_status and project budget actual_spent
                meta = data.get("metadata") or {}
                proposal_id = meta.get("proposal_id")
                project_id = meta.get("project_id")
                org_id = meta.get("organization_id")
                amount_cents = data.get("amount") or 0
                try:
                    if proposal_id:
                        db.table("spending_proposals").update(
                            {"payout_status": "paid"}
                        ).eq("id", proposal_id).execute()
                except Exception:
                    pass
                # Increment project budget actual_spent if budget row exists
                try:
                    if org_id and project_id and amount_cents:
                        amt = (amount_cents or 0) / 100.0
                        # Find the most recent/current budget for the project
                        q = (
                            db.table("budgets")
                            .select("id, actual_spent")
                            .eq("organization_id", org_id)
                            .eq("project_id", project_id)
                            .order("updated_at", desc=True)
                            .limit(1)
                            .execute()
                        )
                        if q.data:
                            b = q.data[0]
                            new_spent = float(b.get("actual_spent") or 0) + amt
                            db.table("budgets").update({"actual_spent": new_spent}).eq(
                                "id", b["id"]
                            ).execute()
                except Exception:
                    pass
        elif evt_type == "payout.failed":
            payout_id = data.get("id")
            if payout_id:
                db.table("transactions").update({"status": "failed"}).eq(
                    "transaction_id", payout_id
                ).execute()
                meta = data.get("metadata") or {}
                proposal_id = meta.get("proposal_id")
                if proposal_id:
                    try:
                        db.table("spending_proposals").update(
                            {"payout_status": "failed"}
                        ).eq("id", proposal_id).execute()
                    except Exception:
                        pass
        elif evt_type == "transfer.paid":
            # Optional: record transfer status updates if needed
            pass
        else:
            # Unhandled events are acknowledged
            pass
        return JSONResponse({"received": True})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
