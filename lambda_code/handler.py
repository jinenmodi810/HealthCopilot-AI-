import json
from utils import textract_helper
from lambda_code import parser  # Avoid using `lambda` as a folder name

def lambda_handler(event, context):
    print("📥 Event received:")
    print(json.dumps(event, indent=2))

    # Step 1: Extract S3 file information
    try:
        record = event['Records'][0]
        bucket_name = record['s3']['bucket']['name']
        object_key = record['s3']['object']['key']
    except (KeyError, IndexError) as e:
        print("❌ Error parsing S3 event:", e)
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid S3 trigger event structure')
        }

    print(f"📂 Processing file: s3://{bucket_name}/{object_key}")

    # Step 2: Use Textract to extract raw text
    try:
        raw_text = textract_helper.extract_text_from_document(bucket_name, object_key)
    except Exception as e:
        print("❌ Textract extraction failed:", e)
        return {
            'statusCode': 500,
            'body': json.dumps('Failed to extract text from document')
        }

    # Step 3: Use parser (LLM / Bedrock) to analyze text
    try:
        parsed_result = parser.process_text(raw_text)
        print("✅ Parsed Result:")
        print(json.dumps(parsed_result, indent=2))
    except Exception as e:
        print("❌ Parser failed:", e)
        return {
            'statusCode': 500,
            'body': json.dumps('AI processing failed')
        }

    # Step 4: Return success
    return {
        'statusCode': 200,
        'body': json.dumps('Document processed successfully.')
    }
