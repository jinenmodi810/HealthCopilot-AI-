import streamlit as st
import boto3
import uuid
import pandas as pd

# Configure AWS
s3_client = boto3.client('s3', region_name="us-east-1")
dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
table = dynamodb.Table('prior_auth_requests')

BUCKET_NAME = "healthcopilot-docs"
UPLOAD_PREFIX = "uploads/"

# Streamlit page config
st.set_page_config(page_title="HealthCopilot Dashboard", page_icon="🩺", layout="wide")

# Custom CSS for styling
st.markdown("""
    <style>
        .centered {
            text-align: left !important;
        }
        .stDataFrame th {
            text-align: left !important;
        }
        .css-1d391kg {  /* success message style */
            background-color: #d4edda;
            color: #155724;
        }
        .css-1v0mbdj { /* error message style */
            background-color: #f8d7da;
            color: #721c24;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🩺 HealthCopilot - Prior Authorization Dashboard")

st.markdown("""
Upload a scanned prior authorization form below. It will be sent to **S3**, then processed by Lambda/Textract/Bedrock, with results shown below.
""")

# File Upload
uploaded_file = st.file_uploader("**Upload a Prior Authorization PDF**", type=["pdf"])

if uploaded_file is not None:
    file_key = f"{UPLOAD_PREFIX}{uploaded_file.name}"
    try:
        s3_client.upload_fileobj(uploaded_file, BUCKET_NAME, file_key)
        st.success(f"✅ Uploaded `{uploaded_file.name}` to S3. Processing will begin automatically.")
    except Exception as e:
        st.error(f"❌ Upload failed: {e}")

st.divider()

# Display requests
st.subheader("📄 All Prior Authorization Requests")

try:
    response = table.scan()
    items = response.get("Items", [])
    if not items:
        st.info("No records found yet. Please upload a PDF above.")
    else:
        df = pd.DataFrame(items)
        
        # Clean up columns
        df["Request ID"] = df["created_at"].apply(lambda x: str(x)[:8])
        df["Form ID"] = df["form_id"].apply(lambda x: x[:8] + "...")
        df["Missing Fields"] = df["missing_fields"].apply(lambda x: ", ".join(x) if isinstance(x, list) and x else "None")

        # only display cleaner columns
        display_df = df[["Request ID", "provider", "npi", "urgency", "Missing Fields", "Form ID"]].rename(
            columns={
                "provider": "Provider",
                "npi": "NPI",
                "urgency": "Urgency",
            }
        )
        
        st.dataframe(display_df, use_container_width=True)

        # Details view
        form_id = st.selectbox(
            "Select a Form ID to view details", df["form_id"].tolist()
        )

        selected = df[df["form_id"] == form_id].iloc[0]
        st.markdown("### 📝 Prior Authorization Details")
        st.markdown(f"""
        **Provider**: {selected['provider']}  
        **NPI**: {selected['npi']}  
        **Urgency**: {selected['urgency']}  
        **Missing Fields**: {', '.join(selected['missing_fields']) if selected['missing_fields'] else 'None'}  
        **Suggested Action**: {selected['suggested_action']}  
        **Status**: {selected['status']}  
        **Form ID**: `{selected['form_id']}`
        """)
except Exception as e:
    st.error(f"❌ DynamoDB error: {e}")
