import json, sys, os
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "data"))
from diagnosis_router import diagnose
from llm_diagnose import llm_diagnose_stub, llm_diagnose
from generate_events import RAZORPAY_ERROR_MAPPING

# For a messy case, the swapped-in gateway_error fully describes a DIFFERENT
# category than decline_code -- recovering the original from that text alone
# is information-theoretically impossible. The well-posed question is: did
# the diagnosis correctly read what the text actually says? This reverse
# lookup recovers that "actually says" target from gateway_error.reason.
REASON_TO_KEY = {v["reason"]: k for k, v in RAZORPAY_ERROR_MAPPING.items()}

with open("data/events.json") as f:
    events = json.load(f)
with open("data/ground_truth.json") as f:
    ground_truth = {g["transaction_id"]: g for g in json.load(f)}

messy_events = [e for e in events if ground_truth[e["transaction_id"]]["is_messy_case"]]
print(f"Evaluating text-reading accuracy on {len(messy_events)} messy-case transactions\n")

has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
llm_available = has_api_key
if not has_api_key:
    print("No ANTHROPIC_API_KEY set -- skipping the real-LLM comparison.\n")

stub_correct, llm_correct, llm_attempted = 0, 0, 0
mismatches_stub, mismatches_llm = [], []
llm_error = None

for event in messy_events:
    text_true_reason = REASON_TO_KEY[event["gateway_error"]["reason"]]

    stub_reason, _, _ = diagnose(event, llm_diagnose_stub)
    if stub_reason == text_true_reason:
        stub_correct += 1
    else:
        mismatches_stub.append((event["transaction_id"], stub_reason, text_true_reason))

    if llm_available:
        try:
            llm_reason, _, _ = diagnose(event, llm_diagnose)
            llm_attempted += 1
            if llm_reason == text_true_reason:
                llm_correct += 1
            else:
                mismatches_llm.append((event["transaction_id"], llm_reason, text_true_reason))
        except Exception as e:
            llm_error = str(e)
            llm_available = False
            print(f"Real LLM call failed, switching to stub-only for the rest of this run: {e}\n")

n = len(messy_events)
print(f"Stub text-reading accuracy: {stub_correct}/{n} ({stub_correct/n*100:.0f}%)")
for txn_id, got, true in mismatches_stub:
    print(f"  MISS  {txn_id}: stub said '{got}', text actually says '{true}'")

if llm_attempted:
    print(f"\nReal LLM text-reading accuracy: {llm_correct}/{llm_attempted} "
          f"({llm_correct/llm_attempted*100:.0f}%)")
    for txn_id, got, true in mismatches_llm:
        print(f"  MISS  {txn_id}: LLM said '{got}', text actually says '{true}'")
elif has_api_key:
    print(f"\nReal LLM comparison unavailable this run: {llm_error}")