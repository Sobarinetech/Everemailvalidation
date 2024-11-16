import streamlit as st
from email_validator import validate_email, EmailNotValidError
import dns.resolver

# Title of the app
st.title("Email ID Authentication")

# Input field for the email
email = st.text_input("Enter an email address to authenticate:")

# Function to validate email
def validate_email_address(email):
    try:
        # Validate syntax and domain
        validation_result = validate_email(email)
        email = validation_result.email  # Corrected email
        domain = email.split('@')[-1]

        # Checking MX records
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            if mx_records:
                return True, "Email is valid and domain is active."
        except dns.resolver.NXDOMAIN:
            return False, "Domain does not exist."
        except dns.resolver.NoAnswer:
            return False, "No MX records found for the domain."
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

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
