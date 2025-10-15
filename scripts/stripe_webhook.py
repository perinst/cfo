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
                db.table("transactions").update({"status": "paid"}).eq(
                    "transaction_id", payout_id
                ).execute()
        else:
            # Unhandled events are acknowledged
            pass
        return JSONResponse({"received": True})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
