import boto3

# use the "bedrock" service (not bedrock-runtime) for profile permission APIs
client = boto3.client("bedrock", region_name="us-east-1")

# replace with your exact profile ID and role ARN
profile_id = "us.anthropic.claude-3-sonnet-20240229-v1:0"
role_arn   = "arn:aws:iam::590183971264:role/healthcopilot-role"

# grant your Lambda role permission to invoke this profile
client.add_inference_profile_permissions(
    inferenceProfileId=profile_id,
    principal=role_arn,
    action="bedrock:InvokeModel"
)

# optional: verify it was added
resp = client.get_inference_profile_permissions(inferenceProfileId=profile_id)
print(resp)
