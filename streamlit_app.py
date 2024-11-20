import streamlit as st
from email_validator import validate_email, EmailNotValidError
import dns.resolver
import smtplib
import socket
import pandas as pd

# Function to check email validity
def validate_email_address(email, custom_sender="test@example.com"):
    """Enhanced email validation with DNS, SMTP, and additional checks."""
    try:
        # Step 1: Syntax validation
        validate_email(email)
    except EmailNotValidError as e:
        return "Invalid", f"Invalid syntax: {str(e)}"
    
    domain = email.split("@")[-1]

    # Step 2: DNS Validation
    try:
        mx_records = dns.resolver.resolve(domain, "MX")
    except dns.resolver.NXDOMAIN:
        return "Invalid", "Domain does not exist."
    except dns.resolver.Timeout:
        return "Invalid", "DNS query timed out."
    except Exception as e:
        return "Invalid", f"DNS error: {str(e)}"

    # Step 3: SMTP Validation
    try:
        mx_host = str(mx_records[0].exchange).rstrip(".")
        smtp = smtplib.SMTP(mx_host, timeout=10)
        smtp.helo()
        smtp.mail(custom_sender)
        code, _ = smtp.rcpt(email)
        smtp.quit()
        if code == 250:
            return "Valid", "Email exists and is reachable."
        elif code == 550:
            return "Invalid", "Mailbox does not exist."
        elif code == 451:
            return "Greylisted", "Temporary error, try again later."
        else:
            return "Invalid", f"SMTP response code {code}."
    except smtplib.SMTPConnectError:
        return "Invalid", "SMTP connection failed."
    except Exception as e:
        return "Invalid", f"SMTP error: {str(e)}"

    return "Invalid", "Unknown error."

# Streamlit App
st.title("Email Validator - Maximum Accuracy")

# Blacklist upload
blacklist_file = st.file_uploader("Upload a blacklist file (optional)", type=["txt"])
blacklist = []
if blacklist_file:
    blacklist = [line.strip() for line in blacklist_file.read().decode("utf-8").splitlines()]
    st.write(f"Loaded {len(blacklist)} blacklisted domains.")

# File upload
uploaded_file = st.file_uploader("Upload a .txt file with emails (50 max)", type=["txt"])
if uploaded_file:
    emails = uploaded_file.read().decode("utf-8").splitlines()
    if len(emails) > 50:
        st.error("File contains more than 50 emails. Please upload a smaller file.")
    else:
        st.write(f"Processing {len(emails)} emails...")
        progress = st.progress(0)
        results = []
        for idx, email in enumerate(emails):
            email = email.strip()
            if email:
                domain = email.split("@")[-1]
                if domain in blacklist:
                    results.append({"Email": email, "Status": "Blacklisted", "Message": "Domain is blacklisted."})
                else:
                    status, message = validate_email_address(email)
                    results.append({"Email": email, "Status": status, "Message": message})
            progress.progress((idx + 1) / len(emails))
        
        # Display results
        df = pd.DataFrame(results)
        st.dataframe(df)

        # Summary report
        valid_count = df[df["Status"] == "Valid"].shape[0]
        invalid_count = df[df["Status"] == "Invalid"].shape[0]
        greylisted_count = df[df["Status"] == "Greylisted"].shape[0]
        blacklisted_count = df[df["Status"] == "Blacklisted"].shape[0]

        st.write("### Summary Report")
        st.write(f"Total Emails: {len(emails)}")
        st.write(f"Valid Emails: {valid_count}")
        st.write(f"Invalid Emails: {invalid_count}")
        st.write(f"Greylisted Emails: {greylisted_count}")
        st.write(f"Blacklisted Emails: {blacklisted_count}")

        # Export results
        csv = df.to_csv(index=False)
        st.download_button("Download Results", data=csv, file_name="email_validation_results.csv", mime="text/csv")
