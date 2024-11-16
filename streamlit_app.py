import streamlit as st
from email_validator import validate_email, EmailNotValidError
import dns.resolver
import smtplib
import socket

# Function to validate emails robustly
def robust_email_validation(email):
    try:
        # Step 1: Validate email syntax
        validate_email(email)

        # Step 2: Check domain existence
        domain = email.split('@')[-1]
        try:
            dns.resolver.resolve(domain, 'A')  # Check if domain has an A record
        except dns.resolver.NXDOMAIN:
            return "Invalid", "Domain does not exist."
        except dns.resolver.NoAnswer:
            return "Invalid", "Domain exists but did not provide an A record."
        except dns.resolver.Timeout:
            return "Invalid", "DNS resolution timed out."

        # Step 3: Check MX records
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            if not mx_records:
                return "Invalid", "No MX records found for the domain."
        except dns.resolver.NoAnswer:
            return "Invalid", "No MX records found for the domain."
        except dns.resolver.Timeout:
            return "Invalid", "MX record lookup timed out."

        # Step 4: Perform SMTP validation
        try:
            mx_host = str(mx_records[0].exchange)  # Get the primary MX host
            smtp = smtplib.SMTP(timeout=10)
            smtp.connect(mx_host)
            smtp.helo()  # Say hello to the server
            smtp.mail('test@example.com')  # Sender's email
            code, message = smtp.rcpt(email)  # Check recipient's email
            smtp.quit()

            if code == 250:
                return "Valid", "Email is valid and exists on the mail server."
            else:
                return "Invalid", "SMTP validation failed. Email does not exist."
        except (socket.gaierror, smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError):
            return "Invalid", "Unable to connect to the mail server."
        except smtplib.SMTPRecipientsRefused:
            return "Invalid", "SMTP server rejected the recipient email."
        except smtplib.SMTPException as e:
            return "Invalid", f"SMTP error: {str(e)}"

    except EmailNotValidError as e:
        return "Invalid", f"Invalid email syntax: {str(e)}"

# Streamlit App
st.title("100% Accurate Email Validation App")

uploaded_file = st.file_uploader("Upload a text file with email IDs (Max: 50)", type=["txt"])

if uploaded_file is not None:
    email_list = uploaded_file.read().decode("utf-8").splitlines()

    if len(email_list) > 50:
        st.error("Upload limit exceeded! Please provide a file with 50 or fewer email IDs.")
    else:
        st.write(f"Processing {len(email_list)} email IDs...")
        progress = st.progress(0)

        results = []
        for idx, email in enumerate(email_list):
            status, message = robust_email_validation(email.strip())
            results.append({"Email": email.strip(), "Status": status, "Message": message})
            progress.progress((idx + 1) / len(email_list))

        # Display results
        import pandas as pd
        results_df = pd.DataFrame(results)
        st.dataframe(results_df)

        # Downloadable CSV
        csv = results_df.to_csv(index=False)
        st.download_button(
            label="Download Validation Results",
            data=csv,
            file_name="validation_results.csv",
            mime="text/csv"
        )
