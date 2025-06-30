import json
import boto3
import os
import uuid
import requests  # new

from utils import textract_helper
from lambda_code import parser

# initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sns_client = boto3.client('sns')
table = dynamodb.Table('prior_auth_requests')
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:590183971264:healthcopilot-alerts"
HEALTHLAKE_ENDPOINT = "https://healthlake.us-east-1.amazonaws.com/datastore/65e74e6cd81e2afd862c4e9dc0b159c1/r4"

# -------------------------------------------------------
# helper function to check HealthLake for patient match
# -------------------------------------------------------
def query_healthlake_patient(name):
    try:
        url = f"{HEALTHLAKE_ENDPOINT}/Patient?name={name}"
        print(f"📡 Querying HealthLake at: {url}")
        response = requests.get(url)
        response.raise_for_status()
        result = response.json()
        if "entry" in result and len(result["entry"]) > 0:
            print(f"✅ HealthLake match found for {name}")
            return True
        else:
            print(f"❌ No match found in HealthLake for {name}")
            return False
    except Exception as e:
        print(f"❌ HealthLake query failed: {e}")
        return False

# -------------------------------------------------------
# main Lambda
# -------------------------------------------------------
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

    # new - query HealthLake to cross-check patient name if available
    patient_name = parsed_result.get("patient_name")
    hl_match = False
    if patient_name:
        hl_match = query_healthlake_patient(patient_name)

    # unique form_id using object key
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
                "healthlake_match": hl_match,   # new field to store match flag
                "status": "pending",
                "created_at": context.aws_request_id,
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

    # check HealthLake connectivity
    try:
        healthlake = boto3.client("healthlake")
        datastore_id = "65e74e6cd81e2afd862c4e9dc0b159c1"
        describe = healthlake.describe_fhir_datastore(
            DatastoreId=datastore_id
        )
        print(f"✅ HealthLake store status: {describe['DatastoreProperties']['DatastoreStatus']}")
    except Exception as e:
        print(f"❌ HealthLake connectivity error: {e}")

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