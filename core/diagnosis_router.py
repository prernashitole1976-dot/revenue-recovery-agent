import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "data"))
from generate_events import RAZORPAY_ERROR_MAPPING


def diagnose(event, llm_diagnose_fn):
    """
    Returns (decline_reason, method, confidence).

    'rule': the event's structured decline_code and its raw gateway_error.reason
    agree with what we'd expect -- fast, free, fully explainable.

    'llm': they disagree (a real-world signal the structured field may be
    stale or wrong) -- defer to the LLM to read the raw description instead.
    """
    expected_reason = RAZORPAY_ERROR_MAPPING.get(event["decline_code"], {}).get("reason")
    actual_reason = event["gateway_error"]["reason"]

    if actual_reason == expected_reason:
        return event["decline_code"], "rule", 1.0

    reason = llm_diagnose_fn(event["gateway_error"]["description"])
    return reason, "llm", 0.7