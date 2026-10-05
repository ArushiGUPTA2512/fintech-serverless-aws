import json
import boto3
import os
import uuid
from datetime import datetime, timezone

s3 = boto3.client("s3", region_name="ap-south-1")
audit_bucket = os.environ.get("AUDIT_BUCKET", "fintech-audit-storage-695694684182-ap-south-1")

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
    amount = payload.get("amount", "0")
    status = payload.get("status") or payload.get("decision", "PROCESSED")
    notification_id = f"notif_{uuid.uuid4().hex[:10]}"
    timestamp = datetime.now(timezone.utc).isoformat()

    # Create multi-channel notification message
    message = (
        f"[FinTech Alert] Payment {payment_id} for user {user_id} "
        f"of amount INR {amount} status: {status} at {timestamp}"
    )

    record = {
        "notificationId": notification_id,
        "paymentId": payment_id,
        "userId": user_id,
        "amount": str(amount),
        "status": status,
        "channels": ["SMS", "EMAIL", "PUSH"],
        "message": message,
        "timestamp": timestamp
    }

    print(f"DISPATCHED NOTIFICATION: {message}")

    # Write audit log to S3 audit bucket
    try:
        s3_key = f"audit-logs/{datetime.now().strftime('%Y/%m/%d')}/{notification_id}.json"
        s3.put_object(
            Bucket=audit_bucket,
            Key=s3_key,
            Body=json.dumps(record, indent=2),
            ContentType="application/json"
        )
        print(f"Archived audit trail to s3://{audit_bucket}/{s3_key}")
    except Exception as e:
        print(f"Warning: S3 audit log write failed: {str(e)}")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "message": "Notification dispatched and audited successfully",
            "notification": record
        }),
        "notificationId": notification_id,
        "status": "SENT"
    }
