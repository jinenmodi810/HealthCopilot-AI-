import json
import boto3
import os
import uuid
import numpy as np
from utils import textract_helper
from lambda_code import parser

# initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sns_client = boto3.client('sns')
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

table = dynamodb.Table('prior_auth_requests')
SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:590183971264:healthcopilot-alerts"

def get_embedding(text):
    body = json.dumps({
        "inputText": text
    })
    try:
        print(f"📌 Sending to Titan model: {body}")
        response = bedrock.invoke_model(
            modelId="amazon.titan-embed-text-v1",
            body=body,
            contentType="application/json",
            accept="application/json"
        )
        raw = response["body"].read()
        print(f"📌 Titan raw response: {raw}")
        parsed = json.loads(raw)
        return parsed.get("embedding", [])
    except Exception as e:
        print(f"❌ Titan embedding EXCEPTION (will re-raise): {e}")
        raise

def cosine_similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    dot = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0
    return dot / (norm1 * norm2)

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

    # Titan embedding
    try:
        embedding = get_embedding(raw_text)
        print(f"✅ Got Titan embedding of length {len(embedding)}")
    except Exception as e:
        print(f"❌ Titan embedding error (final fail): {e}")
        embedding = []

    # unique form_id as object key
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
                "created_at": context.aws_request_id,
                "embedding": embedding,
                "audit_log": [
                    {
                        "changed_by": "system",
                        "timestamp": context.aws_request_id,
                        "new_status": "pending",
                        "comment": "Form uploaded and parsed."
                    }
                ]
            }
        )
        print(f"✅ Stored form_id {form_id} in DynamoDB")
    except Exception as e:
        print(f"❌ DynamoDB storage error: {e}")

    # similarity check
    try:
        previous_items = table.scan().get("Items", [])
        for item in previous_items:
            if item["form_id"] == form_id:
                continue  # skip self
            existing_embedding = item.get("embedding")
            if existing_embedding:
                sim = cosine_similarity(embedding, existing_embedding)
                if sim > 0.9:
                    print(f"⚠️ Duplicate detected with {item['form_id']} similarity={sim:.2f}")
                    table.update_item(
                        Key={"form_id": form_id},
                        UpdateExpression="SET #s = :s",
                        ExpressionAttributeNames={"#s": "status"},
                        ExpressionAttributeValues={":s": "duplicate"}
                    )
                    break
    except Exception as e:
        print(f"❌ Similarity check error: {e}")

    # SNS alert if missing fields
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
