import streamlit as st
from email_validator import validate_email, EmailNotValidError
import dns.resolver
import smtplib
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Function to check SPF and DMARC records
def check_spf_dmarc(domain):
    try:
        spf_records = dns.resolver.resolve(domain, "TXT")
        spf_valid = any("v=spf1" in str(record) for record in spf_records)
    except Exception:
        spf_valid = False

    try:
        dmarc_records = dns.resolver.resolve(f"_dmarc.{domain}", "TXT")
        dmarc_valid = any("v=DMARC1" in str(record) for record in dmarc_records)
    except Exception:
        dmarc_valid = False

    return spf_valid, dmarc_valid

# Enhanced email validation
def validate_email_address(email, blacklist, retries=3, custom_sender="test@example.com"):
    """Robust email validation with advanced checks."""
    try:
        # Step 1: Syntax validation
        validate_email(email)
    except EmailNotValidError as e:
        return email, "Invalid", f"Invalid syntax: {str(e)}"
    
    domain = email.split("@")[-1]

    # Step 2: Blacklist check
    if domain in blacklist:
        return email, "Blacklisted", "Domain is blacklisted."

    # Step 3: DNS Validation
    try:
        mx_records = dns.resolver.resolve(domain, "MX")
    except dns.resolver.NXDOMAIN:
        return email, "Invalid", "Domain does not exist."
    except dns.resolver.Timeout:
        return email, "Invalid", "DNS query timed out."
    except Exception as e:
        return email, "Invalid", f"DNS error: {str(e)}"

    # Step 4: Check SPF and DMARC records
    spf_valid, dmarc_valid = check_spf_dmarc(domain)

    # Step 5: SMTP Validation with retries
    mx_host = str(mx_records[0].exchange).rstrip(".")
    smtp_response = "Unknown error"
    for attempt in range(retries):
        try:
            with smtplib.SMTP(mx_host, timeout=10) as smtp:
                smtp.helo()
                smtp.mail(custom_sender)
                code, _ = smtp.rcpt(email)
                if code == 250:
                    smtp_response = "Valid"
                    break
                elif code == 550:
                    smtp_response = "Invalid: Mailbox does not exist."
                    break
                elif code == 451:
                    smtp_response = "Greylisted: Temporary error, retrying..."
                    time.sleep(5)  # Wait before retrying
                else:
                    smtp_response = f"Invalid: SMTP response code {code}."
        except Exception as e:
            smtp_response = f"SMTP error: {str(e)}"
        if smtp_response.startswith("Valid") or "Invalid" in smtp_response:
            break

    # Consolidate results
    if smtp_response.startswith("Valid"):
        return email, "Valid", "Email exists and is reachable."
    elif smtp_response.startswith("Greylisted"):
        return email, "Greylisted", smtp_response
    else:
        additional_info = []
        if not spf_valid:
            additional_info.append("SPF not configured")
        if not dmarc_valid:
            additional_info.append("DMARC not configured")
        if additional_info:
            smtp_response += f" ({', '.join(additional_info)})"
        return email, "Invalid", smtp_response

# Streamlit App
st.title("Advanced Email Validator - Near 100% Accuracy")

# Blacklist upload
blacklist_file = st.file_uploader("Upload a blacklist file (optional)", type=["txt"])
blacklist = set()
if blacklist_file:
    blacklist = set(line.strip() for line in blacklist_file.read().decode("utf-8").splitlines())
    st.write(f"Loaded {len(blacklist)} blacklisted domains.")

# File upload
uploaded_file = st.file_uploader("Upload a .txt file with emails", type=["txt"])
if uploaded_file:
    emails = uploaded_file.read().decode("utf-8").splitlines()
    st.write(f"Processing {len(emails)} emails...")

    # Process emails in chunks
    chunk_size = 1000  # Adjust based on system capacity
    results = []
    progress = st.progress(0)

    with ThreadPoolExecutor(max_workers=20) as executor:
        for i in range(0, len(emails), chunk_size):
            chunk = emails[i:i + chunk_size]
            futures = [executor.submit(validate_email_address, email.strip(), blacklist) for email in chunk if email.strip()]
            for idx, future in enumerate(as_completed(futures)):
                results.append(future.result())
                if idx % 100 == 0:  # Update progress every 100 emails
                    progress.progress(len(results) / len(emails))

    # Display results
    df = pd.DataFrame(results, columns=["Email", "Status", "Message"])
    st.dataframe(df)

    # Summary report
    st.write("### Summary Report")
    st.write(f"Total Emails: {len(emails)}")
    for status in ["Valid", "Invalid", "Greylisted", "Blacklisted"]:
        count = df[df["Status"] == status].shape[0]
        st.write(f"{status} Emails: {count}")

    # Export results
    csv = df.to_csv(index=False)
    st.download_button("Download Results", data=csv, file_name="email_validation_results.csv", mime="text/csv")
