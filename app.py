import streamlit as st
import boto3
import pandas as pd
import json
from io import BytesIO
from xhtml2pdf import pisa

# -------------
# AWS configuration
# -------------
s3_client = boto3.client('s3', region_name="us-east-1")
dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
table = dynamodb.Table('prior_auth_requests')
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

BUCKET_NAME = "healthcopilot-docs"
UPLOAD_PREFIX = "uploads/"

st.set_page_config(page_title="HealthCopilot Dashboard", page_icon="🩺", layout="wide")

# Custom CSS
st.markdown("""
    <style>
        .stButton>button {
            border-radius: 8px;
            background-color: #4CAF50;
            color: white;
            border: 2px solid #4CAF50;
        }
        .stButton>button:hover {
            background-color: #45a049;
        }
        .stProgress>div>div>div>div {
            background-color: #4CAF50 !important;
        }
        .duplicate-warning {
            background-color: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #f5c6cb;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🩺 HealthCopilot - Prior Authorization Dashboard")

st.markdown("""
Upload a scanned prior authorization form below. It will be sent to **S3**, then processed by Lambda/Textract/Bedrock, with results shown below.
""")

uploaded_file = st.file_uploader("**Upload a Prior Authorization PDF**", type=["pdf"])

if uploaded_file:
    file_key = f"{UPLOAD_PREFIX}{uploaded_file.name}"
    try:
        s3_client.upload_fileobj(uploaded_file, BUCKET_NAME, file_key)
        st.success(f"✅ Uploaded `{uploaded_file.name}` to S3. Processing will begin automatically.")
    except Exception as e:
        st.error(f"❌ Upload failed: {e}")

st.divider()

st.subheader("📄 All Prior Authorization Requests")

# ---------------------
# Bedrock recommender
# ---------------------
def bedrock_recommend(missing_fields, context):
    prompt = f"""
    The following prior authorization request is missing these fields: {', '.join(missing_fields)}.
    Based on your knowledge of healthcare prior auth processes, suggest what other information might be useful to complete it.
    Context:
    {context}
    """
    body = json.dumps({"inputText": prompt})
    response = bedrock.invoke_model(
        modelId="amazon.titan-text-lite-v1",
        body=body,
        contentType="application/json",
        accept="application/json"
    )
    result = json.loads(response["body"].read())
    return result.get("results", [{}])[0].get("outputText", "No suggestions available.")

try:
    response = table.scan()
    items = response.get("Items", [])
    if not items:
        st.info("No records found yet. Please upload a PDF above.")
    else:
        df = pd.DataFrame(items)
        df["Request ID"] = df["created_at"].apply(lambda x: str(x)[:8])
        df["Form ID"] = df["form_id"].apply(lambda x: x[:8] + "...")
        df["Missing Fields"] = df["missing_fields"].apply(lambda x: ", ".join(x) if isinstance(x, list) and x else "None")

        def highlight_duplicates(val):
            return "color: red;" if val == "duplicate" else ""
        
        styled_df = df[["Request ID", "provider", "npi", "urgency", "Missing Fields", "status", "Form ID"]].rename(
            columns={
                "provider": "Provider",
                "npi": "NPI",
                "urgency": "Urgency",
                "status": "Status"
            }
        ).style.applymap(highlight_duplicates, subset=["Status"])

        st.dataframe(styled_df, use_container_width=True)

        form_id = st.selectbox("Select a Form ID to view details", df["form_id"].tolist())
        selected = df[df["form_id"] == form_id].iloc[0]

        st.markdown("### 📝 Prior Authorization Details")

        if selected['status'] == "duplicate":
            st.markdown("""
                <div class="duplicate-warning">
                    ⚠️ This request appears to be a duplicate of a previous submission. Please review carefully.
                </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        **Provider**: {selected['provider']}  
        **NPI**: {selected['npi']}  
        **Urgency**: {selected['urgency']}  
        **Missing Fields**: {', '.join(selected['missing_fields']) if selected['missing_fields'] else 'None'}  
        **Suggested Action**: {selected['suggested_action']}  
        **Status**: {selected['status']}  
        **Form ID**: `{selected['form_id']}`
        """)

        # Add Bedrock suggestion button
        if st.button("💡 Get AI Suggestions for Missing Fields"):
            with st.spinner("Thinking with Bedrock..."):
                try:
                    suggestion = bedrock_recommend(
                        selected['missing_fields'] if isinstance(selected['missing_fields'], list) else [],
                        selected['suggested_action']
                    )
                    st.chat_message("ai").write(suggestion)
                except Exception as e:
                    st.error(f"Bedrock suggestion failed: {e}")

        # workflow progress
        status_map = {
            "pending": 0,
            "under_review": 50,
            "approved": 100,
            "denied": 100,
            "duplicate": 0
        }
        st.progress(status_map.get(selected['status'], 0))

        new_status = st.selectbox(
            "Update Status",
            options=["pending", "under_review", "approved", "denied", "duplicate"],
            index=["pending", "under_review", "approved", "denied", "duplicate"].index(selected['status'])
        )
        comment = st.text_input("Add comment for audit trail (optional)")

        if st.button("Save Status"):
            try:
                audit_entry = {
                    "changed_by": "Admin",
                    "new_status": new_status,
                    "timestamp": pd.Timestamp.now().isoformat(),
                    "comment": comment or ""
                }

                table.update_item(
                    Key={"form_id": selected["form_id"]},
                    UpdateExpression="""
                        SET #s = :s,
                            audit_log = list_append(if_not_exists(audit_log, :empty_list), :entry)
                    """,
                    ExpressionAttributeNames={"#s": "status"},
                    ExpressionAttributeValues={
                        ":s": new_status,
                        ":entry": [audit_entry],
                        ":empty_list": []
                    }
                )
                st.success(f"✅ Status updated to {new_status} with audit log recorded.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to update status or audit log: {e}")

        if selected.get("audit_log"):
            st.markdown("### 🕒 Audit Trail")
            for entry in selected['audit_log']:
                with st.expander(f"{entry['timestamp']} — {entry['changed_by']} changed status to {entry['new_status']}"):
                    st.markdown(f"""
                    **Status:** `{entry['new_status']}`  
                    **Comment:** {entry['comment'] or '_No comment_'}
                    """)
        else:
            st.info("No audit history yet for this form.")

        if st.button("Download Details as PDF"):
            try:
                html_content = f"""
                <h2>Prior Authorization Details</h2>
                <ul>
                    <li><b>Provider:</b> {selected['provider']}</li>
                    <li><b>NPI:</b> {selected['npi']}</li>
                    <li><b>Urgency:</b> {selected['urgency']}</li>
                    <li><b>Missing Fields:</b> {', '.join(selected['missing_fields']) if selected['missing_fields'] else 'None'}</li>
                    <li><b>Suggested Action:</b> {selected['suggested_action']}</li>
                    <li><b>Status:</b> {selected['status']}</li>
                    <li><b>Form ID:</b> {selected['form_id']}</li>
                </ul>
                """
                result = BytesIO()
                pisa.CreatePDF(html_content, dest=result)
                st.download_button(
                    label="📄 Download Details as PDF",
                    data=result.getvalue(),
                    file_name=f"prior_auth_{selected['form_id']}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"❌ Failed to generate PDF: {e}")

except Exception as e:
    st.error(f"❌ DynamoDB error: {e}")