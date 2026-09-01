# core/constraints.py

# Daily capacity per action -- modeling real-world limits: WhatsApp/SMS
# provider rate limits, gateway retry quotas, and collections team hours.
DAILY_CAPACITY = {
    "retry": 40,
    "switch_method": 20,
    "nudge": 25,
    "escalate": 10,
}

# Hard compliance rules -- these override ERV entirely, no exceptions.
# Modeled on real constraints: RBI discourages blind repeated auto-debit
# retries on hard declines, and outreach outside reasonable hours is a
# customer-experience (and in some read-ings, regulatory) risk.
def passes_compliance(event, decline_reason, action):
    if decline_reason in ("do_not_honor", "card_blocked", "risk_flagged_by_bank") and action == "retry":
        return False, "hard decline -- auto-retry blocked, must nudge or escalate"
    if event["attempt_number"] > 3:
        return False, "attempt cap reached -- must escalate, no further auto-actions"
    return True, None