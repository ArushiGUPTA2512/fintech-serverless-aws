import json
from datetime import datetime, timezone

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, default=str))

    # EventBridge sends detail field; Step Functions passes payload directly
    payload = event
    if "detail" in event:
        payload = event["detail"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                pass
    elif "body" in event and event["body"]:
        if isinstance(event["body"], str):
            try:
                payload = json.loads(event["body"])
            except Exception:
                pass

    payment_id = payload.get("paymentId", "pay_unknown")
    user_id = payload.get("userId", "user_unknown")
    raw_amount = payload.get("amount", 0.0)
    try:
        amount = float(raw_amount)
    except Exception:
        amount = 0.0

    timestamp = datetime.now(timezone.utc).isoformat()

    # FinTech Fraud Risk Engine Logic
    if amount > 100000:
        risk_level = "HIGH"
        decision = "BLOCKED"
        fraud_score = 95
        reason = "Transaction amount exceeds high-risk threshold (INR 100,000)"
    elif amount >= 50000:
        risk_level = "MEDIUM"
        decision = "FLAGGED_FOR_REVIEW"
        fraud_score = 55
        reason = "Transaction amount requires secondary step-up authorization"
    else:
        risk_level = "LOW"
        decision = "APPROVED"
        fraud_score = 10
        reason = "Standard transaction within normal risk parameters"

    result = {
        "paymentId": payment_id,
        "userId": user_id,
        "amount": amount,
        "riskLevel": risk_level,
        "decision": decision,
        "fraudScore": fraud_score,
        "reason": reason,
        "evaluatedAt": timestamp
    }

    print(f"Fraud Assessment Result: {json.dumps(result)}")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result),
        # Direct dictionary fields for Step Functions JSONPath state machine integration
        "riskLevel": risk_level,
        "decision": decision,
        "fraudScore": fraud_score,
        "paymentId": payment_id,
        "userId": user_id,
        "amount": amount
    }
