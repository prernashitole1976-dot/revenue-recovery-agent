import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "core"))
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from webhook_logic import process_payment_failed
from constraints import DAILY_CAPACITY

app = FastAPI(title="Revenue Recovery Agent -- Live Webhook")
remaining_capacity = dict(DAILY_CAPACITY)


class RazorpayWebhookPayload(BaseModel):
    entity: str = "event"
    event: str = "payment.failed"
    payload: dict
    customer_tenure_months: int = 6
    transaction_id_override: Optional[str] = None


@app.post("/webhook/payment-failed")
def handle_payment_failed(body: RazorpayWebhookPayload):
    global remaining_capacity
    payment_entity = body.payload.get("payment", {}).get("entity")
    if not payment_entity:
        raise HTTPException(status_code=400, detail="Missing payload.payment.entity")

    response, remaining_capacity = process_payment_failed(
        payment_entity,
        customer_tenure_months=body.customer_tenure_months,
        transaction_id_override=body.transaction_id_override,
        remaining_capacity=remaining_capacity,
    )
    if "error" in response:
        raise HTTPException(status_code=422, detail=response["error"])
    return response


@app.get("/capacity")
def get_capacity():
    return remaining_capacity


@app.post("/reset-capacity")
def reset_capacity():
    global remaining_capacity
    remaining_capacity = dict(DAILY_CAPACITY)
    return {"status": "reset", "remaining_capacity_today": remaining_capacity}


@app.get("/")
def root():
    return {
        "service": "Revenue Recovery Agent -- Live Webhook",
        "endpoints": ["POST /webhook/payment-failed", "GET /capacity", "POST /reset-capacity"],
    }