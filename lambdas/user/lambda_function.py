import json
import boto3
import os
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
table_name = os.environ.get("USERS_TABLE", "FinTechUsers")
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, default=str))
    
    # Handle API Gateway proxy integration or direct invoke
    body = event
    if "body" in event and event["body"]:
        if isinstance(event["body"], str):
            try:
                body = json.loads(event["body"])
            except Exception:
                body = event["body"]
        else:
            body = event["body"]

    user_id = body.get("userId") or f"user_{int(datetime.now().timestamp())}"
    name = body.get("name", "Anonymous User")
    email = body.get("email", "user@example.com")
    tier = body.get("tier", "STANDARD")
    created_at = datetime.now(timezone.utc).isoformat()

    item = {
        "userId": user_id,
        "name": name,
        "email": email,
        "tier": tier,
        "createdAt": created_at,
        "status": "ACTIVE"
    }

    try:
        table.put_item(Item=item)
        print(f"Successfully created user {user_id} in {table_name}")
        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "User created successfully",
                "user": item
            }, default=str)
        }
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": "Failed to create user",
                "details": str(e)
            })
        }
