# core/promise_to_pay.py
import json, re, os
from datetime import datetime, timedelta

INTENTS = ["reschedule", "cancel", "dispute", "unclear"]


def parse_reply_stub(reply_text: str, today=None) -> dict:
    """Offline keyword+regex version -- zero setup, good for testing."""
    today = today or datetime(2026, 8, 20)
    text = reply_text.lower()

    if any(w in text for w in ["cancel", "not interested", "stop"]):
        return {"intent": "cancel", "reschedule_date": None}
    if any(w in text for w in ["already paid", "check", "wrong charge"]):
        return {"intent": "dispute", "reschedule_date": None}

    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, day in enumerate(weekdays):
        if day in text:
            days_ahead = (i - today.weekday() + 7) % 7 or 7
            return {"intent": "reschedule", "reschedule_date": (today + timedelta(days=days_ahead)).date().isoformat()}
    if "next week" in text:
        return {"intent": "reschedule", "reschedule_date": (today + timedelta(days=7)).date().isoformat()}

    return {"intent": "unclear", "reschedule_date": None}


def parse_reply_llm(reply_text: str) -> dict:
    """Real LLM version -- pip install anthropic, set ANTHROPIC_API_KEY."""
    import os as _os
    from anthropic import Anthropic
    client = Anthropic(api_key=_os.environ.get("ANTHROPIC_API_KEY"))
    prompt = (
        "A customer replied to a payment-failure follow-up message. Classify their intent as "
        "exactly one of: reschedule, cancel, dispute, unclear. If reschedule, also extract the "
        "implied date as YYYY-MM-DD (assume today is 2026-08-20). "
        f'Reply: "{reply_text}"\n\n'
        'Respond as JSON only: {"intent": "...", "reschedule_date": "YYYY-MM-DD or null"}'
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=60,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        return json.loads(response.content[0].text.strip())
    except (json.JSONDecodeError, IndexError):
        return {"intent": "unclear", "reschedule_date": None}


if __name__ == "__main__":
    with open("data/customer_replies.json") as f:
        replies = json.load(f)

    results = []
    for r in replies:
        parsed = parse_reply_stub(r["reply_text"])  # swap to parse_reply_llm once API key is set
        results.append({**r, **parsed})
        print(f"{r['transaction_id']}: \"{r['reply_text'][:50]}...\" -> {parsed['intent']}"
              + (f", reschedule {parsed['reschedule_date']}" if parsed["reschedule_date"] else ""))

    with open("reports/promise_to_pay_results.json", "w") as f:
        json.dump(results, f, indent=2)