import boto3

# Create a Textract client using boto3
textract = boto3.client('textract')

def extract_text_from_document(bucket_name, document_key):
    """
    Extracts text from a document stored in S3 using Amazon Textract.
    
    Args:
        bucket_name (str): Name of the S3 bucket
        document_key (str): Key (filename) of the uploaded document
    
    Returns:
        str: All extracted text lines combined into a single string
    """

    print(f"📤 Calling Textract for: s3://{bucket_name}/{document_key}")

    # Call Textract to detect text
    response = textract.detect_document_text(
        Document={
            'S3Object': {
                'Bucket': bucket_name,
                'Name': document_key
            }
        }
    )

    # Loop through the result and collect LINE-type blocks
    lines = []
    for block in response.get('Blocks', []):
        if block['BlockType'] == 'LINE':
            lines.append(block['Text'])

    # Join all lines into a single string with line breaks
    extracted_text = '\n'.join(lines)

    print(f"📝 Extracted {len(lines)} lines of text.")
    return extracted_text
