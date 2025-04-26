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
class AuthWrapper:
    def login(self, *args, **kwargs):
        # Invoke the Streamlit main login/signup flow
        main()
        # Retrieve login status and username from session state
        logged = st.session_state.get("logged_in", False)
        user = st.session_state.get("username", "")
        return user, logged, user

def load_auth():
    """Provides an authenticator object with a login() method."""
    return AuthWrapper()
import streamlit as st
from database import create_user, authenticate

# Simple login/signup UI

def login():
    st.title("Login or Sign Up")
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

    with tab_login:
        email = st.text_input("Gmail", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if email and password:
                user = authenticate(email, password)
                if user:
                    st.session_state.user_id = user.id
                    st.session_state.username = user.name
                    st.session_state.logged_in = True
                    st.success(f"Welcome back, {user.name}!")
                    st.experimental_rerun()
                else:
                    st.error("Invalid email or password")
            else:
                st.error("Please enter both email and password")

    with tab_signup:
        new_name = st.text_input("Name", key="signup_name")
        new_email = st.text_input("Gmail", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Sign Up"):
            if new_name and new_email and new_password:
                user = create_user(new_name, new_email, new_password)
                if user:
                    st.success("Account created! Please log in.")
                else:
                    st.error("Name or email already exists.")
            else:
                st.error("Please fill all fields")
