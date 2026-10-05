import json
import boto3
import os
import uuid
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
table_name = os.environ.get("TRANSACTIONS_TABLE", "FinTechTransactions")
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, default=str))

    # Check if this is an API Gateway GET request with pathParameters
    http_method = event.get("httpMethod")
    path_parameters = event.get("pathParameters") or {}

    if http_method == "GET" or ("transactionId" in path_parameters):
        transaction_id = path_parameters.get("transactionId") or event.get("transactionId")
        if not transaction_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Missing transactionId parameter"})
            }
        
        try:
            response = table.get_item(Key={"transactionId": transaction_id})
            item = response.get("Item")
            if not item:
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"message": f"Transaction {transaction_id} not found"})
                }
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"transaction": item}, default=str)
            }
        except Exception as e:
            print(f"Error reading transaction: {str(e)}")
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": str(e)})
            }

    # Otherwise, it's a request to record a transaction (e.g. from Step Functions or POST)
    payload = event
    if "body" in event and event["body"]:
        if isinstance(event["body"], str):
            try:
                payload = json.loads(event["body"])
            except Exception:
                payload = event["body"]
        else:
            payload = event["body"]

    transaction_id = payload.get("transactionId") or f"txn_{uuid.uuid4().hex[:10]}"
    payment_id = payload.get("paymentId", "pay_unknown")
    user_id = payload.get("userId", "user_unknown")
    amount = str(payload.get("amount", "0.0"))
    status = payload.get("status", "COMPLETED")
    timestamp = datetime.now(timezone.utc).isoformat()

    item = {
        "transactionId": transaction_id,
        "paymentId": payment_id,
        "userId": user_id,
        "amount": amount,
        "status": status,
        "timestamp": timestamp,
        "details": payload.get("details", "Core settlement finalized")
    }

    try:
        table.put_item(Item=item)
        print(f"Stored transaction: {transaction_id} in {table_name}")
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": "Transaction recorded successfully",
                "transaction": item
            }, default=str),
            # Return flat keys directly for easy Step Functions chaining
            "transactionId": transaction_id,
            "paymentId": payment_id,
            "status": status,
            "amount": amount
        }
    except Exception as e:
        print(f"Error storing transaction: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
