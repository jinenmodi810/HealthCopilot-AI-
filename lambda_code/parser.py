import boto3
import json
import re

bedrock = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")

def process_text(raw_text):
    messages = [
        {
            "role": "user",
            "content": f"""
You are a skilled medical prior authorization assistant. Analyze the following prior authorization form text and return JSON:
{{
  "provider": "",
  "npi": "",
  "urgency": "",
  "missing_fields": [],
  "suggested_action": ""
}}

Form text:
{raw_text}
"""
        }
    ]

    try:
        response = bedrock.invoke_model(
            modelId="arn:aws:bedrock:us-east-1:590183971264:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            body=json.dumps({
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.2,
                "anthropic_version": "bedrock-2023-05-31"
            }),
            accept="application/json",
            contentType="application/json"
        )

        response_body = json.loads(response['body'].read())
        print("🧠 Bedrock raw output:", response_body)

        completion = response_body["content"][0]["text"]

        # extract only the first JSON object with a regex
        match = re.search(r"\{.*?\}", completion, re.DOTALL)
        if match:
            clean_json = match.group(0)
            parsed = json.loads(clean_json)
            return parsed
        else:
            print("No valid JSON found in Claude output.")
            return {
                "provider": None,
                "npi": None,
                "urgency": None,
                "missing_fields": [],
                "suggested_action": "Manual review required"
            }

    except Exception as e:
        print("❌ Bedrock parsing error:", e)
        return {
            "provider": None,
            "npi": None,
            "urgency": None,
            "missing_fields": [],
            "suggested_action": "Manual review required"
        }
