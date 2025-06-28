import json
import boto3
import os
import uuid
from utils import textract_helper
from lambda_code import parser  # after you renamed your folder

# initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sns_client = boto3.client('sns')
table = dynamodb.Table('prior_auth_requests')

SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:590183971264:healthcopilot-alerts"

def lambda_handler(event, context):
    print(f"📥 Event received:\n{json.dumps(event)}")
    
    # get the uploaded file info from S3 event
    record = event['Records'][0]
    bucket_name = record['s3']['bucket']['name']
    object_key = record['s3']['object']['key']
    
    print(f"📂 Processing file: s3://{bucket_name}/{object_key}")

    # Textract OCR
    raw_text = textract_helper.extract_text_from_document(bucket_name, object_key)
    print(f"📝 Extracted {len(raw_text.splitlines())} lines of text.")

    # Claude parsing
    try:
        parsed_result = parser.process_text(raw_text)
    except Exception as e:
        print(f"❌ Bedrock parsing error: {e}")
        parsed_result = {}

    print(f"✅ Parsed Result:\n{json.dumps(parsed_result)}")

    # generate unique form_id
    form_id = object_key 

    # store in DynamoDB
    try:
        table.put_item(
            Item={
                "form_id": form_id,
                "provider": parsed_result.get("provider", "unknown"),
                "npi": parsed_result.get("npi", "unknown"),
                "urgency": parsed_result.get("urgency", "unknown"),
                "missing_fields": parsed_result.get("missing_fields", []),
                "suggested_action": parsed_result.get("suggested_action", ""),
                "status": "pending",
                "created_at": context.aws_request_id
            }
        )
        print(f"✅ Stored form_id {form_id} in DynamoDB")
    except Exception as e:
        print(f"❌ DynamoDB storage error: {e}")

    # send SNS alert if missing fields found
    missing_fields = parsed_result.get("missing_fields", [])
    if missing_fields:
        message = (
            f"⚠️ Missing fields detected in prior authorization form:\n\n"
            f"Provider: {parsed_result.get('provider', 'unknown')}\n"
            f"NPI: {parsed_result.get('npi', 'unknown')}\n"
            f"Urgency: {parsed_result.get('urgency', 'unknown')}\n"
            f"Missing Fields: {', '.join(missing_fields)}\n"
            f"Suggested Action: {parsed_result.get('suggested_action', '')}\n"
            f"Form ID: {form_id}"
        )
        try:
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="HealthCopilot Alert: Missing Fields in Prior Auth Form",
                Message=message
            )
            print("✅ SNS alert published successfully.")
        except Exception as e:
            print(f"❌ SNS publish error: {e}")

    return {
        "statusCode": 200,
        "body": json.dumps("Document processed successfully.")
    }
