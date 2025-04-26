import streamlit as st
from database import create_user, authenticate

def main():
    st.set_page_config(page_title="Login / Signup", layout="centered")
    st.title("Login or Sign Up")

    # Tabs for Login and Signup
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

    with tab_login:
        st.subheader("Login")
        email = st.text_input("Gmail", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if email and password:
                user = authenticate(email, password)
                if user:
                    st.success(f"Welcome {user.name}! You have logged in successfully.")
                    st.session_state["user_id"] = user.id
                    st.session_state["username"] = user.name
                    st.session_state["logged_in"] = True
                    st.experimental_rerun()
                else:
                    st.error("Invalid email or password")
            else:
                st.error("Please enter both email and password")

    with tab_signup:
        st.subheader("Sign Up")
        new_name = st.text_input("Name", key="signup_name")
        new_email = st.text_input("Gmail", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Sign Up"):
            if new_name and new_email and new_password:
                user = create_user(new_name, new_email, new_password)
                if user:
                    st.success("Account created successfully! Please go to Login.")
                else:
                    st.error("Error: User with this email or name already exists.")
            else:
                st.error("Please fill all fields")
                
if __name__ == "__main__":
    main()
