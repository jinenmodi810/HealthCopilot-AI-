# HealthCopilot: Serverless Prior Authorization Tracker for U.S. Patients

## 🩺 Overview
HealthCopilot is a serverless, AI-powered application built using AWS Lambda to help U.S. patients and healthcare clinics track insurance prior authorization requests. It automates document processing, detects missing information, and sends timely alerts via SMS or email.

## 🚀 Features
- Upload scanned prior auth forms to S3
- Automatically extract key fields using Amazon Textract
- Use Amazon Bedrock (Claude/Mistral) to analyze extracted text
- Classify provider, urgency, and detect missing fields using LLM prompts
- Store structured data in DynamoDB
- Send alerts using SNS or Twilio for missing/incomplete submissions
- Schedule reminders using Amazon EventBridge

## 🧠 AI/ML Capabilities
HealthCopilot leverages AI to enhance healthcare workflow automation:
- **Amazon Textract** extracts raw text from scanned documents.
- **Amazon Bedrock (Claude/Mistral)** is used to:
  - Identify missing fields in the authorization form
  - Classify urgency (Routine/Urgent)
  - Extract or validate insurance provider
  - Suggest next actions based on form content
- [Optional] Amazon Comprehend can analyze patient responses to detect intent (e.g., "already submitted", "cancel", etc.)

## 🔁 AI Prompt Example (used with Bedrock)
```
Given the following extracted text from a healthcare prior authorization form, identify:
1. Insurance Provider
2. Urgency Level (Routine/Urgent/Unknown)
3. NPI Number
4. Whether required fields are missing
5. Suggested next action
```

## 🛠️ Architecture Diagram
![Architecture](link-to-uploaded-diagram.png)

## ⚙️ AWS Services Used
| Service        | Purpose                                              |
|----------------|-------------------------------------------------------|
| AWS Lambda     | Core logic for processing and alerts                 |
| Amazon S3      | Store uploaded documents                             |
| Amazon Textract| Extract text fields from scanned forms               |
| Amazon Bedrock | LLM-based AI prompt processing (Claude/Mistral)     |
| DynamoDB       | Store structured metadata from parsed forms          |
| Amazon SNS     | Send notifications (can be replaced by Twilio)       |
| Amazon EventBridge | Schedule periodic follow-ups                   |

## 📂 Project Structure
```
healthcopilot/
├── lambda/
│   ├── handler.py
│   ├── parser.py
│   └── notifier.py
├── eventbridge/
│   └── check_status.py
├── utils/
│   └── textract_helper.py
├── templates/
│   └── sample_prior_auth.pdf
├── README.md
└── requirements.txt
```

## 📥 Setup Instructions
1. Clone the repo:
   ```bash
   git clone https://github.com/your-username/healthcopilot.git
   cd healthcopilot
   ```

2. Deploy Lambda functions using AWS Console or SAM CLI.
3. Create an S3 bucket and configure it to trigger `handler.py` Lambda.
4. Set up DynamoDB table `prior_auth_requests`.
5. Enable Amazon Textract and Bedrock permissions for Lambda IAM role.
6. Configure SNS (or Twilio) with verified phone numbers or email.
7. Add EventBridge rule to run `check_status.py` every 3 days.

## 🧪 How It Works
1. Clinic uploads prior auth form → triggers Lambda
2. Lambda sends to Textract → extracts text
3. Text sent to Bedrock → identifies key values and missing fields
4. Parsed data saved to DynamoDB → alerts triggered if needed
5. EventBridge triggers follow-up notifications for stale entries

## 🎥 Demo Video
[Watch the demo here](https://youtu.be/example)

## 📜 License
MIT License
