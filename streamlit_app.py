import streamlit as st
from validate_email_address import validate_email, EmailNotValidError
import dns.resolver

# Title of the app
st.title("Email ID Authentication")

# Input field for the email
email = st.text_input("Enter an email address to authenticate:")

# Function to validate email
def validate_email_address(email):
    try:
        # Syntax validation
        is_valid = validate_email(email, check_format=True)
        if not is_valid:
            return False, "Invalid email format."

        # Extracting the domain
        domain = email.split('@')[-1]

        # Checking if the domain has MX records
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            if mx_records:
                return True, "Email is valid and domain is active."
        except dns.resolver.NXDOMAIN:
            return False, "Domain does not exist."
        except dns.resolver.NoAnswer:
            return False, "No MX records found for the domain."

    except EmailNotValidError as e:
        return False, str(e)

    return False, "Unknown error occurred."

# Button to trigger validation
if st.button("Validate Email"):
    if email:
        is_valid, message = validate_email_address(email)
        if is_valid:
            st.success(message)
        else:
            st.error(message)
    else:
        st.warning("Please enter an email address.")
