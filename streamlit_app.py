import streamlit as st
from email_validator import validate_email, EmailNotValidError
import dns.resolver
import smtplib
import socket


def validate_email_address(email):
    """Performs robust email validation with syntax, DNS, and SMTP checks."""
    try:
        # Step 1: Syntax validation
        validate_email(email)
    except EmailNotValidError as e:
        return "Invalid", f"Invalid email syntax: {str(e)}"

    domain = email.split("@")[-1]

    # Step 2: DNS (Domain) Validation
    try:
        # Check if domain has A or MX records
        dns.resolver.resolve(domain, "A")
        mx_records = dns.resolver.resolve(domain, "MX")
        if not mx_records:
            return "Invalid", "Domain exists but has no MX records."
    except dns.resolver.NXDOMAIN:
        return "Invalid", "Domain does not exist."
    except dns.resolver.NoAnswer:
        return "Invalid", "No MX records found for the domain."
    except dns.resolver.Timeout:
        return "Invalid", "DNS query timed out."
    except Exception as e:
        return "Invalid", f"DNS validation failed: {str(e)}"

    # Step 3: SMTP Validation
    try:
        # Connect to the mail server
        mx_host = str(mx_records[0].exchange).rstrip(".")  # Get the top-priority mail server
        smtp = smtplib.SMTP(mx_host, timeout=10)
        smtp.helo()
        smtp.mail("test@example.com")  # Sender's email
        code, _ = smtp.rcpt(email)  # Check recipient's email
        smtp.quit()

        # Interpret SMTP response codes
        if code == 250:
            return "Valid", "Email is valid and exists."
        elif code == 550:
            return "Invalid", "Email does not exist on the server."
        else:
            return "Invalid", f"SMTP server rejected the email with code {code}."
    except smtplib.SMTPRecipientsRefused:
        return "Invalid", "SMTP server rejected the recipient email."
    except smtplib.SMTPConnectError:
        return "Invalid", "Could not connect to the SMTP server."
    except smtplib.SMTPServerDisconnected:
        return "Invalid", "SMTP server disconnected unexpectedly."
    except Exception as e:
        return "Invalid", f"SMTP validation failed: {str(e)}"

    return "Invalid", "Unknown error occurred."


# Streamlit App
st.title("Ultimate Email Validator - 100% Precision")

# File Upload Section
uploaded_file = st.file_uploader("Upload a .txt file containing email IDs (limit: 50)", type=["txt"])

if uploaded_file is not None:
    email_list = uploaded_file.read().decode("utf-8").splitlines()

    if len(email_list) > 50:
        st.error("Upload limit exceeded! Please provide a file with 50 or fewer email IDs.")
    else:
        st.write(f"Processing {len(email_list)} email IDs...")
        progress = st.progress(0)

        results = []
        for idx, email in enumerate(email_list):
            email = email.strip()
            if email:  # Skip empty lines
                status, message = validate_email_address(email)
                results.append({"Email": email, "Status": status, "Message": message})
            progress.progress((idx + 1) / len(email_list))

        # Display Results
        import pandas as pd
        results_df = pd.DataFrame(results)
        st.dataframe(results_df)

        # Provide CSV Download Option
        csv = results_df.to_csv(index=False)
        st.download_button(
            label="Download Results",
            data=csv,
            file_name="email_validation_results.csv",
            mime="text/csv"
        )
