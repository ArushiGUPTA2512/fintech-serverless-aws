import json
import boto3
import os
import uuid
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
events_client = boto3.client("events", region_name="ap-south-1")

payments_table_name = os.environ.get("PAYMENTS_TABLE", "FinTechPayments")
event_bus_name = os.environ.get("EVENT_BUS_NAME", "FinTechEventBus")
payments_table = dynamodb.Table(payments_table_name)

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, default=str))

    # Parse body from API Gateway proxy or direct invocation
    body = event
    if "body" in event and event["body"]:
        if isinstance(event["body"], str):
            try:
                body = json.loads(event["body"])
            except Exception:
                body = event["body"]
        else:
            body = event["body"]

    payment_id = body.get("paymentId") or f"pay_{uuid.uuid4().hex[:10]}"
    user_id = body.get("userId", "user_default")
    amount = float(body.get("amount", 0.0))
    currency = body.get("currency", "INR")
    recipient_id = body.get("recipientId", "merchant_default")
    timestamp = datetime.now(timezone.utc).isoformat()

    item = {
        "paymentId": payment_id,
        "userId": user_id,
        "amount": str(amount),
        "currency": currency,
        "recipientId": recipient_id,
        "status": "PENDING",
        "createdAt": timestamp
    }

    try:
        # 1. Store payment in DynamoDB
        payments_table.put_item(Item=item)
        print(f"Payment record saved to DynamoDB: {payment_id} with status PENDING")

        # 2. Publish PaymentCreated event to EventBridge
        event_payload = {
            "paymentId": payment_id,
            "userId": user_id,
            "amount": amount,
            "currency": currency,
            "recipientId": recipient_id,
            "status": "PENDING",
            "timestamp": timestamp
        }

        eb_response = events_client.put_events(
            Entries=[
                {
                    "Source": "fintech.payment",
                    "DetailType": "PaymentCreated",
                    "Detail": json.dumps(event_payload),
                    "EventBusName": event_bus_name
                }
            ]
        )
        print(f"EventBridge PutEvents response: {eb_response}")

        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Payment initiated successfully",
                "payment": item,
                "eventBridgeEntries": eb_response.get("Entries", [])
            }, default=str)
        }
    except Exception as e:
        print(f"Error processing payment: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": "Failed to initiate payment",
                "details": str(e)
            })
        }
