# app.py
import streamlit as st
from auth import load_auth
from database import init_db, Session, User, Emission
import carbon_logic as cl
from datetime import date

# 1. Initialize DB
init_db()

# 2. Authentication
authenticator = load_auth()
name, authentication_status, username = authenticator.login("Login", "main")
if not authentication_status:
    st.stop()

# 3. Greeting & “Let’s get started” button
st.write(f"👋 Welcome {name}, let’s get started with your Carbon Foot Calculator.")
if st.button("Let’s get started"):
    st.session_state.started = True

if not st.session_state.get("started"):
    st.stop()

# 4. Sidebar menu
menu = st.sidebar.radio("Navigate", [
    "Carbon Data",
    "Carbon Metre",
    "Emission Analysis",
    "Year & Month Analysis",
    "Download"
])

# 5. Get DB session & current user
db = Session()
user = db.query(User).filter_by(name=name).first()

def log_emission(category, facility, year, month, value):
    entry = Emission(
      user_id  = user.id,
      date     = date(int(year), list(cl.MONTHS).index(month)+1, 1),
      facility = facility,
      category = category,
      value    = value
    )
    db.add(entry)
    db.commit()

# 6. Handle each menu choice
if menu == "Carbon Data":
    # show input widgets (facility, year, month, categories)
    # on submit: value = cl.calculate_...(...)
    # call log_emission(...)
    pass

elif menu == "Carbon Metre":
    # query db for this user/year/month & call plot_gauge
    pass

elif menu == "Emission Analysis":
    # select year, month, facility → pull entries & show breakdown, table, charts
    pass

elif menu == "Year & Month Analysis":
    # compare multiple years or facilities
    pass

elif menu == "Download":
    # build a DataFrame from user.emissions
    # st.download_button for CSV
    # zip charts if needed
    pass
