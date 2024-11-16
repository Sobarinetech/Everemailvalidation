import streamlit as st
from email_validator import validate_email, EmailNotValidError
import dns.resolver
import time
import pandas as pd

# Title
st.title("Enhanced Email Validation App")

# File upload
uploaded_file = st.file_uploader("Upload a text file with email IDs (Max: 50)", type=["txt"])

# Validation logic
def validate_email_address(email):
    try:
        validation_result = validate_email(email)
        domain = email.split('@')[-1]
        # Check domain MX records
        try:
            dns.resolver.resolve(domain, 'MX')
            return "Valid", "Email is valid."
        except Exception as e:
            return "Invalid", f"Domain check failed: {str(e)}"
    except EmailNotValidError as e:
        return "Invalid", str(e)

if uploaded_file is not None:
    email_list = uploaded_file.read().decode("utf-8").splitlines()
    
    # Restrict to 50 IDs
    if len(email_list) > 50:
        st.error("Upload limit exceeded! Please provide a file with 50 or fewer email IDs.")
    else:
        # Remove duplicates
        unique_emails = list(set(email_list))
        st.write(f"Processing {len(unique_emails)} unique email IDs...")
        
        # Validation results
        results = []
        progress = st.progress(0)
        for idx, email in enumerate(unique_emails):
            status, message = validate_email_address(email)
            results.append({"Email": email, "Status": status, "Message": message})
            progress.progress((idx + 1) / len(unique_emails))
            time.sleep(0.1)  # Simulate processing delay

        # Show results
        results_df = pd.DataFrame(results)
        st.dataframe(results_df)
        
        # Download results
        csv = results_df.to_csv(index=False)
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name="validation_results.csv",
            mime="text/csv"
        )
        
        # Domain summary
        domains = [email.split('@')[-1] for email in unique_emails]
        domain_summary = pd.DataFrame(pd.Series(domains).value_counts(), columns=["Count"])
        st.bar_chart(domain_summary)
