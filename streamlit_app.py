import streamlit as st
import dns.resolver
import smtplib
import pandas as pd
from email_validator import validate_email, EmailNotValidError
from concurrent.futures import ThreadPoolExecutor, as_completed

def validate_email_address(email, blacklist):
    try:
        v = validate_email(email)
        email = v["email"]
    except EmailNotValidError as e:
        return email, "Invalid", str(e)

    domain = email.split("@")[-1]
    if domain in blacklist:
        return email, "Blacklisted", "Domain is blacklisted."

    try:
        mx_records = dns.resolver.resolve(domain, "MX")
        if len(mx_records) == 0:
            return email, "Invalid", "No MX records found."
    except dns.resolver.NXDOMAIN:
        return email, "Invalid", "Domain does not exist."
    except Exception as e:
        return email, "Invalid", f"DNS error: {str(e)}"

    try:
        mx_host = str(mx_records[0].exchange).rstrip(".")
        smtp = smtplib.SMTP(mx_host, timeout=10)
        smtp.helo()
        smtp.mail("test@example.com")
        code, _ = smtp.rcpt(email)
        smtp.quit()
        if code == 250:
            return email, "Valid", "Email exists and is reachable."
        elif code == 550:
            return email, "Invalid", "Mailbox does not exist."
        elif code == 451:
            return email, "Greylisted", "Temporary error, try again later."
        else:
            return email, "Invalid", f"SMTP response code {code}."
    except Exception as e:
        return email, "Invalid", f"SMTP error: {str(e)}"


def main():
    st.title("Email Validator")
    blacklist_file = st.file_uploader("Upload blacklist file (optional)", type=["txt"])
    blacklist = set()
    if blacklist_file:
        blacklist = {line.strip().lower() for line in blacklist_file.read().decode("utf-8").splitlines()}

    uploaded_file = st.file_uploader("Upload .txt file with emails", type=["txt"])
    if uploaded_file:
        emails = uploaded_file.read().decode("utf-8").splitlines()
        st.write(f"Processing {len(emails)} emails...")

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(validate_email_address, email.strip().lower(), blacklist) for email in emails if email.strip()]
            results = [future.result() for future in as_completed(futures)]

        df = pd.DataFrame(results, columns=["Email", "Status", "Message"])
        st.dataframe(df)

        st.write("### Summary Report")
        st.write(f"Total Emails: {len(emails)}")
        for status in ["Valid", "Invalid", "Greylisted", "Blacklisted"]:
            count = df[df["Status"] == status].shape[0]
            st.write(f"{status} Emails: {count}")

        csv = df.to_csv(index=False)
        st.download_button("Download Results", data=csv, file_name="email_validation_results.csv", mime="text/csv")


if __name__ == "__main__":
    main()
