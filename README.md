# NeuroLens: AI-Powered Cognitive Load Estimator for Remote Teams

## 🧠 Overview
NeuroLens is a serverless, AI-driven application built using AWS Lambda that helps remote teams detect cognitive overload and burnout risk. It analyzes work patterns from metadata like calendar events, email activity, and task updates to provide early nudges, improving productivity and well-being.

## 🚀 Features
- Triggered every few hours using Amazon EventBridge
- Simulated metadata input: calendar meetings, unread messages, emails sent, tasks completed
- Uses Amazon Bedrock (Claude/Mistral) to estimate cognitive load based on patterns
- Detects high cognitive load and sends alerts to Slack or email via SNS/Twilio
- Stores user score and overload history in DynamoDB
- Mock Slack/Trello integration for fast, demo-friendly setup

## 🧠 AI/ML Capabilities
NeuroLens leverages large language models (LLMs) and metadata-driven logic:

- **Amazon Bedrock (Claude/Mistral)** used to:
  - Analyze metadata trends
  - Estimate burnout risk / cognitive overload
  - Suggest actions (take break, reschedule meetings, etc.)
- [Optional] **Amazon Comprehend** to evaluate sentiment from Slack/email messages

## 🔁 AI Prompt Example (used with Bedrock)
```
Given the following metadata:
- Calendar meetings today: 6
- Unread Slack messages: 54
- Emails sent: 15
- Tasks completed: 1
Estimate cognitive load score (0-100), burnout risk level, and suggest a wellness action.
```

## 🛠️ Architecture Diagram
![Architecture](link-to-uploaded-diagram.png)

## ⚙️ AWS Services Used
| Service            | Purpose                                                    |
|--------------------|-------------------------------------------------------------|
| AWS Lambda         | Core logic for scoring and notifications                   |
| Amazon EventBridge | Periodic check trigger (every 3 hours)                     |
| Amazon Bedrock     | AI analysis of cognitive load                              |
| Amazon SNS         | Sends alert via Slack webhook, email, or SMS               |
| DynamoDB           | Stores user score history and timestamps                   |
| [Optional] Comprehend | Analyze sentiment of team messages                    |

## 📂 Project Structure
```
neurolens/
├── lambda_code/
│   ├── handler.py
│   ├── parser.py
│   └── notifier.py
├── eventbridge/
│   └── check_status.py
├── utils/
│   └── bedrock_helper.py
├── mockdata/
│   └── user_metadata_sample.json
├── README.md
└── requirements.txt
```

## 📥 Setup Instructions
1. Clone the repo:
   ```bash
   git clone https://github.com/your-username/neurolens.git
   cd neurolens
   ```

2. Deploy Lambda functions using AWS Console or SAM CLI.
3. Configure EventBridge to trigger `handler.py` Lambda every 3 hours.
4. Set up DynamoDB table `cognitive_load_profiles`.
5. Enable Bedrock and Comprehend permissions for Lambda role.
6. Mock Slack API or use print logs for notification simulation.

## 🧪 How It Works
1. EventBridge triggers Lambda based on time or simulated input
2. Lambda fetches or receives metadata (meetings, messages, tasks)
3. Data sent to Bedrock → returns load score, risk, and suggestion
4. Alerts (or mock messages) sent if score > threshold
5. Results stored in DynamoDB

## 🎥 Demo Video
[Watch the demo here](https://youtu.be/example)

## 📜 License
MIT License