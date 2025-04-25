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
    def plot_gauge(current_value, category, safe_limit):
    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw={'projection': 'polar'})
    ax.set_theta_offset(np.pi/2)
    ax.set_theta_direction(-1)

    # Dynamic scaling with 25% buffer
    max_limit = safe_limit * 1.25
    display_value = min(current_value, max_limit)

    # Angle calculations
    theta_max = 0.75 * np.pi  # 135 degrees
    theta_min = -theta_max     # -135 degrees
    total_range = theta_max - theta_min  # 270 degrees

    # Calculate angles
    safe_angle = (safe_limit/max_limit) * total_range
    excess_angle = ((display_value - safe_limit)/max_limit) * total_range if current_value > safe_limit else 0

    # Background arc (full range)
    ax.barh(1, total_range, height=0.4, left=theta_min, color='#f0f0f0', alpha=0.3)

    # Safe zone (green)
    ax.barh(1, safe_angle, height=0.4, left=theta_min, color='#2ecc71', alpha=0.7)

    # Excess zone (red)
    if current_value > safe_limit:
        ax.barh(1, excess_angle, height=0.4,
               left=theta_min + safe_angle, color='#e74c3c', alpha=0.7)

    # Needle
    needle_angle = theta_min + (display_value/max_limit) * total_range
    ax.plot([needle_angle, needle_angle], [0, 1.2], color='#2c3e50', lw=2.5)

    # Arc labels
    label_values = [0, safe_limit, max_limit]
    label_angles = [theta_min + (v/max_limit)*total_range for v in label_values]
    ax.set_xticks(label_angles)
    ax.set_xticklabels(
        [f'{v/1000:.0f}k' if v < 10000 else f'{v/1000:.1f}k' for v in label_values],
        color='#666',
        fontsize=10
    )

    # Center text
    plt.text(0, 0, f'{current_value/1000:.1f}k\nCO₂',
             ha='center', va='center',
             fontsize=14,
             color='#2c3e50',
             fontweight='bold')

    # Styling
    ax.set_yticks([])
    ax.spines[:].set_visible(False)
    plt.title(category, pad=20, fontsize=14, color='#2c3e50', fontweight='bold')
    plt.tight_layout()
    return fig

emission_factors= {
    "Fossil Fuels": {
        "CNG": 2.21,  # kg CO₂ per Kg
    },
    "Fossil Fuels per litre": {
        "Petrol/Gasoline": 2.315,
        "Diesel": 2.68,
        "LPG": 1.51
    },
    "Fossil Fuels per scm": {
        "PNG": 2.1
    },
    "Electricity": {
        "Coal/Thermal": 0.85,  # kg CO₂ per kWh
        "Solar": 0.00  # No emissions
    },
    "Travel": {
        "Airways": 0.133,  # kg CO₂ per km
        "Roadways": 0.271,
        "Railways": 0.041
    }
}

# Global Warming Potential (GWP) values for fugitive emission
f_e_f = {
    "Domestic Refrigeration": 1430,  # Example: R-134a
    "Commercial Refrigeration": 3922,  # Example: R-404A
    "Industrial Refrigeration": 2088,  # Example: R-410A
    "Residential and Commercial A/C": 1650  # Example: R-407C
}

# Emission factors for different electricity sources (kg CO₂ per kWh)
e_e_f = {
    "Coal/Thermal": 0.92,  # High emissions
    "Solar": 0.05  # Almost negligible emissions
}

# Emission factor for water (kg CO₂e per cubic meter)
w_e_f = 0.344



# Emission factors (kg CO₂e per kg of waste) by waste and treatment type
wa_e_f = {
        "Household Residue": {"Landfills": 1.0, "Combustion": 0.7, "Recycling": 0.2, "Composting": 0.1},
        "Food and Drink Waste": {"Landfills": 1.9, "Combustion": 0.8, "Recycling": 0.3, "Composting": 0.05},                                                  "Garden Waste": {"Landfills": 0.6, "Combustion": 0.4, "Recycling": 0.2, "Composting": 0.03},
    "Commercial and Industrial Waste": {"Landfills": 2.0, "Combustion": 1.5, "Recycling": 0.6, "Composting": 0.2}
}

SAFE_LIMITS = {
    "Fossil Fuels": 5000,    # kg CO₂
    "Fugitive": 3000,
    "Electricity": 4000,
    "Water": 2000,
    "Waste": 1500,
    "Travel": 3500
}


# Offset factors (approximate, per unit per month)
of_e_f = {
    "tree": 1.75,              # Monthly offset per tree
    "soil": 0.0515,                     # kg CO₂e/m²/month
    "grass": 0.0309,                    # kg CO₂e/m²/month
    "water": 0.0412                     # kg CO₂e/m²/month
}



# Set Streamlit page config
st.set_page_config(layout="wide", page_title="Carbon Footprint Calculator")

# Initialize session state for slide tracking
if "slide_index" not in st.session_state:
    st.session_state.slide_index = 0

if "emission_log" not in st.session_state:
    st.session_state.emission_log = []



# Define slides content
slides = [
    {"title": "Fossil Fuels", "content": "", "calculator": True},
    {"title": "Fugitive", "content": "How fugitive impacts the footprint"},
    {"title": "Electricity", "content": "electricity consumption details"},
    {"title": "Water", "content": "Water consumption details."},
    {"title": "Waste", "content": "Waste management insights."},
    {"title": "Travel", "content": "How travel impacts the footprint."},
    {"title": "Offset", "content": "Ways to offset carbon footprint."},
    {"title": "Summary", "content": "Carbon Footprint Summary"}
]

# Function to go to the next slide
def next_slide():
    if st.session_state.slide_index < len(slides) - 1:
        st.session_state.slide_index += 1

# Function to go to the previous slide
def prev_slide():
    if st.session_state.slide_index > 0:
        st.session_state.slide_index -= 1

# Display current slide
current_slide = slides[st.session_state.slide_index]
st.title(current_slide["title"])
st.write(current_slide["content"])



# If the slide is "Fossil Fuels", show the Carbon Footprint Calculator
if current_slide["title"] == "Fossil Fuels":
    st.header("Carbon Footprint Calculator")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Facility")
        facility1 = st.selectbox("", ["Choose Facility", "Residential Areas", "Hostels", "Academic Area",
                                    "Health Centre", "Schools", "Visitor's Hostel", "Servants Quarters", "Shops/Bank/PO"])

        st.subheader("Year")
        year1 = st.selectbox("", ["Choose Year", "2024", "2023", "2022", "2021", "2020", "2019", "2018", "2017", "2016", "2015"])

        st.subheader("Month")
        month1 = st.selectbox("", ["Choose Month", "January", "February", "March", "April", "May", "June",
                                  "July", "August", "September", "October", "November", "December"])

    with col2:
        st.subheader("Fuel Type")
        fuel_type1 = st.selectbox("", ["Choose Fuel Type", "CNG", "Petrol/Gasoline", "Diesel", "PNG", "LPG"])

        st.subheader("Unit")
        unit1 = st.selectbox("", ["Choose Unit", "Kg", "Tonne","litre","SCM"])

        st.subheader("Amount Consumed")
        amount_consumed1 = st.number_input("Enter Amount", min_value=1, max_value=10000)

    if fuel_type1 != "Choose Fuel Type" and unit1 != "Choose Unit":
        factor = None
        if unit1 == "Tonne":
            amount_consumed1 *= 1000  # Convert to kg
            factor = emission_factors["Fossil Fuels"].get(fuel_type1)
        elif unit1 == "litre":
            factor = emission_factors["Fossil Fuels per litre"].get(fuel_type1)
        elif unit1 == "SCM":
            factor = emission_factors["Fossil Fuels per scm"].get(fuel_type1)
        elif unit1 == "kg":
            factor = emission_factors["Fossil Fuels"].get(fuel_type1)
        if factor is not None:
            carbon_footprint =amount_consumed1 * factor

            st.subheader("Estimated Carbon Emission")
            st.write(f"Your estimated CO₂ emission: **{carbon_footprint:.2f} kg CO₂**")
# Store in session state
            st.session_state["Fossil Fuels Emission"] = carbon_footprint
            if facility1 != "Choose Facility" and year1 != "Choose Year" and month1 != "Choose Month":
                st.session_state.emission_log.append({
                    "Year": year1,
                    "Month": month1,
                    "Facility": facility1,
                    "Factor": "Fossil Fuels",
                    "Emission": carbon_footprint
                })


elif current_slide["title"] == "Fugitive":
    st.header("Carbon Footprint Calculator")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Facility")
        facility2 = st.selectbox("", ["Choose Facility", "Residential Areas", "Hostels", "Academic Area",
                                    "Health Centre", "Schools", "Visitor's Hostel", "Servants Quarters", "Shops/Bank/PO"])

        st.subheader("Year")
        year2 = st.selectbox("", ["Choose Year", "2024", "2023", "2022", "2021", "2020", "2019", "2018", "2017", "2016", "2015"])

        st.subheader("Month")
        month2 = st.selectbox("", ["Choose Month", "January", "February", "March", "April", "May", "June",
                                  "July", "August", "September", "October", "November", "December"])

    with col2:
        st.subheader("apllication type")
        application_type2 = st.selectbox("", ["Choose application Type", "Domestic Refrigeration", "Commercial Refrigeration", "Industrial Refrigeration", "Residential and Commercial A/C"])

        st.subheader("Units")
        unit2 = st.selectbox("", ["Choose Unit", "Kg", "Tonne"])

        st.subheader("number of units")
        amount_consumed2 = st.number_input("Enter number of units", min_value=1, max_value=10000)

    if application_type2 != "Choose application Type":
        gwp_factor = f_e_f[application_type2]  # Get GWP value
        if unit2 == "Tonne":
            amount_consumed2 *= 1000  # Convert tonnes to kg

        fugitive_emission = amount_consumed2 * gwp_factor  # Calculate CO₂ equivalent

        st.subheader("Estimated Carbon Emission")
        st.write(f"Your estimated CO₂ equivalent emission: **{fugitive_emission:.2f} kg CO₂**")
        st.session_state["Fugitive Emission"] = fugitive_emission

        if facility2 != "Choose Facility" and year2 != "Choose Year" and month2 != "Choose Month":
            st.session_state.emission_log.append({
               "Year": year2,
               "Month": month2,
               "Facility": facility2,
               "Factor": "Fugitive",
               "Emission":fugitive_emission
            })


elif current_slide["title"] == "Electricity":
    st.header("Carbon Footprint Calculator")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Facility")
        facility3 = st.selectbox("", ["Choose Facility", "Residential Areas", "Hostels", "Academic Area",
                                    "Health Centre", "Schools", "Visitor's Hostel", "Servants Quarters", "Shops/Bank/PO"])

        st.subheader("Year")
        year3 = st.selectbox("", ["Choose Year", "2024", "2023", "2022", "2021", "2020", "2019", "2018", "2017", "2016", "2015"])

        st.subheader("Month")
        month3 = st.selectbox("", ["Choose Month", "January", "February", "March", "April", "May", "June",
                                  "July", "August", "September", "October", "November", "December"])

    with col2:
        st.subheader("electricity type")
        electricity_type3 = st.selectbox("", ["Choose electricity Type", "Coal/Thermal", "Solar"])

        st.subheader("Electricity Source")
        elec_sou3=st.selectbox("",["Choose Electricity Source", "Purchased", "Self-Produced"])

        st.subheader("Unit")
        unit3 = st.selectbox("", ["Choose Unit", "KWH"])

        st.subheader("Amount Consumed")
        amount_consumed3 = st.number_input("Enter Amount", min_value=1, max_value=10000)

    if electricity_type3 != "Choose electricity Type":
        emission_factor = e_e_f[electricity_type3]  # Get emission factor
        electricity_emission = amount_consumed3 * emission_factor  # Calculate CO₂ equivalent

        st.subheader("Estimated Carbon Emission")
        st.write(f"Your estimated CO₂ equivalent emission: **{electricity_emission:.2f} kg CO₂**")

        # Store in session state for further calculations
        st.session_state["Electricity Emission"] = electricity_emission

        if facility3 != "Choose Facility" and year3 != "Choose Year" and month3 != "Choose Month":
            st.session_state.emission_log.append({
               "Year": year3,
               "Month": month3,
               "Facility": facility3,
               "Factor": "Electricity",
               "Emission": electricity_emission
            })

elif current_slide["title"] == "Water":
    st.header("Carbon Footprint Calculator")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Facility")
        facility4 = st.selectbox("", ["Choose Facility", "Residential Areas", "Hostels", "Academic Area",
                                    "Health Centre", "Schools", "Visitor's Hostel", "Servants Quarters", "Shops/Bank/PO"])

        st.subheader("Year")
        year4 = st.selectbox("", ["Choose Year", "2024", "2023", "2022", "2021", "2020", "2019", "2018", "2017", "2016", "2015"])

        st.subheader("Month")
        month4 = st.selectbox("", ["Choose Month", "January", "February", "March", "April", "May", "June",
                                  "July", "August", "September", "October", "November", "December"])

    with col2:
        st.subheader("Water Type")
        fuel_type4 = st.selectbox("", ["Choose Water Type", "Supplied Water", "Treated water"])

        st.subheader("Discharge Site")
        dis_site4= st.text_input("Enter Discharge Site")

        st.subheader("Unit")
        unit4 = st.selectbox("", ["Choose Unit", "Cubic metre", "million litres"])

        st.subheader("Amount")
        amount_consumed4 = st.number_input("Enter Amount", min_value=1, max_value=10000)

    water_emission = 0
    if unit4 == "Cubic metre":
        water_emission = amount_consumed4 * w_e_f
    elif unit4 == "million litres":
        # 1 million litre = 1000 m³
        water_emission = amount_consumed4 * 1000 * w_e_f

    st.subheader("Estimated Carbon Emission")
    st.write(f"Your estimated CO₂ equivalent emission from water usage is: **{water_emission:.2f} kg CO₂e**")

    st.session_state["Water Emission"] = water_emission

    if facility4 != "Choose Facility" and year4 != "Choose Year" and month4 != "Choose Month":
        st.session_state.emission_log.append({
            "Year": year4,
            "Month": month4,
            "Facility": facility4,
            "Factor": "Water",
            "Emission": water_emission
        })

elif current_slide["title"] == "Waste":
    st.header("Carbon Footprint Calculator")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Facility")
        facility5 = st.selectbox("", ["Choose Facility", "Residential Areas", "Hostels", "Academic Area",
                                    "Health Centre", "Schools", "Visitor's Hostel", "Servants Quarters", "Shops/Bank/PO"])

        st.subheader("Year")
        year5 = st.selectbox("", ["Choose Year", "2024", "2023", "2022", "2021", "2020", "2019", "2018", "2017", "2016", "2015"])

        st.subheader("Month")
        month5 = st.selectbox("", ["Choose Month", "January", "February", "March", "April", "May", "June",
                                  "July", "August", "September", "October", "November", "December"])

    with col2:
        st.subheader("Waste Type")
        waste_type5 = st.selectbox("", ["Choose Waste Type", "Household Residue", "Food and Drink Waste", "Garden Waste", "Commercial and Industrial Waste"])

        st.subheader("Treatment Type")
        treatment_type5 =st.selectbox("", ["Chooose Treatment Type", "Landfills", "Combustion", "Recycling", "Composting"])

        st.subheader("Unit")
        unit5 = st.selectbox("", ["Choose Unit", "Kg", "Tonne"])

        st.subheader("Amount")
        amount_consumed5 = st.number_input("Enter Amount", min_value=1, max_value=10000)

    emission_factor = wa_e_f.get(waste_type5, {}).get(treatment_type5, 0)
    amount_kg = amount_consumed5 * 1000 if unit5 == "Tonne" else amount_consumed5
    waste_emission = amount_kg * emission_factor

    st.subheader("Estimated Carbon Emission")
    st.write(f"Your estimated CO₂ equivalent emission from waste is: **{waste_emission:.2f} kg CO₂e**")

    st.session_state["Waste Emission"] = waste_emission

    if facility5 != "Choose Facility" and year5 != "Choose Year" and month5 != "Choose Month":
        st.session_state.emission_log.append({
            "Year": year5,
            "Month": month5,
            "Facility": facility5,
            "Factor": "Waste",
            "Emission": waste_emission
        })

elif current_slide["title"] == "Travel":
    st.header("Carbon Footprint Calculator")
    col1, col2 = st.columns(2)
    emission=0.0
    with col1:
        st.subheader("Facility")
        facility6 = st.selectbox("", ["Choose Facility", "Residential Areas", "Hostels", "Academic Area",
                                    "Health Centre", "Schools", "Visitor's Hostel", "Servants Quarters", "Shops/Bank/PO"],key ="facility_travel")

        st.subheader("Year")
        year6 = st.selectbox("", ["Choose Year", "2024", "2023", "2022", "2021", "2020", "2019", "2018", "2017", "2016", "2015"],key="year_travel")

        st.subheader("Month")
        month6 = st.selectbox("", ["Choose Month", "January", "February", "March", "April", "May", "June",
                                  "July", "August", "September", "October", "November", "December"],key="month_travel")

    with col2:
        if "travel_emissions" not in st.session_state:                      
            st.session_state.travel_emissions = 0.0
        st.subheader(" Mode of Transport")
        travel_mode = st.selectbox("", ["Choose Mode of Transport", "Airways", "Roadways", "Railways"],key="transport_mode")
        if travel_mode == "Airways":
            flight_length = st.selectbox("Flight Length", ["Short Haul", "Long Haul", "Domestic", "International"],key="air_flight_length")
            flight_emissions = {
            "Short Haul": 0.15,
            "Long Haul": 0.11,
            "Domestic": 0.18,
            "International": 0.13
            }
            distance = st.number_input("Enter distance traveled (km)", min_value=0.0, step=1.0,key="air_distance_input")
            if distance > 0:
                emission = distance * flight_emissions[flight_length]
                st.session_state["Travel Emission"] = emission
                st.session_state.travel_emissions += emission
                st.write(f"Estimated Emissions: {emission:.2f} kg CO₂e")
        elif travel_mode == "Railways":
             rail_type = st.selectbox("Rail Type", ["Metro", "National Railways"],key="rail_type")
             if rail_type == "Metro":
                 emission_factor = 0.04
                 distance = st.number_input("Enter distance traveled (km)", min_value=0.0, step=1.0,key="rail_train_type")
                 if distance > 0:
                     emission = distance * emission_factor
                     st.session_state["Travel Emission"] = emission
                     st.session_state.travel_emissions += emission
                     st.write(f"Estimated Emissions: {emission:.2f} kg CO₂e")
             elif rail_type == "National Railways":
                 train_type = st.selectbox("Train Type", ["Electric", "Diesel", "Hydrogen"],key="train_type")
                 train_emission_factors = {
                    "Electric": 0.035,
                    "Diesel": 0.06,
                    "Hydrogen": 0.04
             }
             distance = st.number_input("Enter distance traveled (km)", min_value=0.0, step=1.0,key="train_distance")
             if distance > 0:
                 emission = distance * train_emission_factors[train_type]   
                 st.session_state["Travel Emission"] = emission
                 st.session_state.travel_emissions += emission              
                 st.write(f"Estimated Emissions: {emission:.2f} kg CO₂e")
        elif travel_mode == "Roadways":
              ownership = st.selectbox("Vehicle Ownership", ["Public", "Personal"], key="raod_ownership")

              if ownership == "Personal":
                  vehicle_type = st.selectbox("Vehicle Type", ["Small Sized Car", "Medium Sized Car", "Large Sized Car", "Motorcycle"], key="road_personal_vehicle_type")
                  personal_emission_factors = {
                     "Small Sized Car": 0.12,
                     "Medium Sized Car": 0.17,
                     "Large Sized Car": 0.22,
                     "Motorcycle": 0.09
                  }
                  distance = st.number_input("Enter distance traveled (km)", min_value=0.0, step=1.0,  key="road_personal_distance")
                  if distance > 0:
                      emission = distance * personal_emission_factors[vehicle_type]
                      st.session_state["Travel Emission"] = emission        
                      st.session_state.travel_emissions += emission
                      st.write(f"Estimated Emissions: {emission:.2f} kg CO₂e")
              elif ownership == "Public":
                  vehicle_type = st.selectbox("Vehicle Type", ["Bus", "Taxi"], key="road_public_vehicle_type")

                  if vehicle_type == "Bus":                                                                                                             
                       bus_fuel = st.selectbox("Bus Runs On", ["Electricity", "Diesel", "Hydrogen"], key="bus_fuel_type")                               
                       bus_emission_factors = {
                         "Electricity": 0.03,
                         "Diesel": 0.09,
                         "Hydrogen": 0.05
                       }
                       distance = st.number_input("Enter distance traveled (km)", min_value=0.0, step=1.0, key="road_bus_distance")
                       if distance > 0:
                           emission = distance * bus_emission_factors[bus_fuel]
                           st.session_state["Travel Emission"] = emission
                           st.session_state.travel_emissions += emission
                           st.write(f"Estimated Emissions: {emission:.2f} kg CO₂e")
                  elif vehicle_type == "Taxi":
                       taxi_fuel = st.selectbox("Taxi Runs On", ["Electricity", "Petrol", "Hydrogen", "CNG"], key="taxi_fuel_type")
                       taxi_emission_factors = {
                          "Electricity": 0.06,
                          "Petrol": 0.16,
                          "Hydrogen": 0.07,
                          "CNG": 0.13
                       }
                       distance = st.number_input("Enter distance traveled (km)", min_value=0.0, step=1.0, key="road_taxi_distance")
                       if distance > 0:
                           emission = distance * taxi_emission_factors[taxi_fuel]
                           st.session_state["Travel Emission"] = emission
                           st.session_state.travel_emissions += emission
                           st.write(f"Estimated Emissions: {emission:.2f} kg CO₂e")

        st.subheader("Total Travel Emission")
        st.write(f"Your estimated CO₂ emission: **{st.session_state.travel_emissions:.2f} kg CO₂**")


        if facility6 != "Choose Facility" and year6 != "Choose Year" and month6 != "Choose Month":
            st.session_state.emission_log.append({
               "Year": year6,
               "Month": month6,
               "Facility": facility6,
               "Factor": "Travel",
               "Emission": emission
            })
elif current_slide["title"] == "Offset":
    st.header("Carbon Footprint Calculator")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Facility")
        facility7 = st.selectbox("", ["Choose Facility", "Residential Areas", "Hostels", "Academic Area",
                                    "Health Centre", "Schools", "Visitor's Hostel", "Servants Quarters", "Shops/Bank/PO"])

        st.subheader("Year")
        year7 = st.selectbox("", ["Choose Year", "2024", "2023", "2022", "2021", "2020", "2019", "2018", "2017", "2016", "2015"])

        st.subheader("Month")
        month7 = st.selectbox("", ["Choose Month", "January", "February", "March", "April", "May", "June",
                                  "July", "August", "September", "October", "November", "December"])

        st.subheader("Area Covered Under Water(m^2)")
        water_consum7 = st.number_input("water covered area Area", min_value=1, max_value=10000)

    with col2:
        st.subheader("Number of Trees in the Facility")
        trees_count7 = st.number_input("trees covered number", min_value=1, max_value=10000)

        st.subheader("Area Covered Under Soil(m^2)")
        soil_area7 = st.number_input("soil covered area Area", min_value=1, max_value=10000)

        st.subheader("Area Covered Under Grass(m^2)")
        grass_area7 = st.number_input("grass covered area Area", min_value=1, max_value=10000)

    st.session_state["trees_count7"] = trees_count7
    st.session_state["soil_area7"] = soil_area7
    st.session_state["grass_area7"] = grass_area7
    st.session_state["water_consum7"] = water_consum7


    tree_offset = trees_count7 * of_e_f["tree"]
    soil_offset = soil_area7 * of_e_f["soil"]
    grass_offset = grass_area7 * of_e_f["grass"]
    water_offset = water_consum7 * of_e_f["water"]

    total_offset = tree_offset + soil_offset + grass_offset + water_offset

    st.subheader("Estimated Offset")
    st.write(f"Your estimated **CO₂ offset** for this month is: **{total_offset:.2f} kg CO₂e**")

    st.session_state["Offset Emission"] = total_offset

    if facility7 != "Choose Facility" and year7 != "Choose Year" and month7 != "Choose Month":
        st.session_state.emission_log.append({
            "Year": year7,
            "Month": month7,
            "Facility": facility7,
            "Factor": "Offset",
            "Emission": -total_offset  # Negative for reduction
        })


# Navigation buttons
col1, col2 = st.columns([1, 1])
with col1:
    if st.session_state.slide_index > 0:
        st.button("Previous", on_click=prev_slide)
with col2:
    if st.session_state.slide_index < len(slides) - 1:
        st.button("submit", on_click=next_slide)


    pass

elif menu == "Carbon Metre":
    st.header("Carbon Footprint Summary")

    # Year/Month Filter
    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.selectbox("Select Year",
                                   reversed(["2024","2023","2022","2021","2020",
                                            "2019","2018","2017","2016","2015"]))
    with col2:
        selected_month = st.selectbox("Select Month",
                                    ["January","February","March","April","May","June",
                                     "July","August","September","October","November","December"])

    # Calculate emissions
    category_totals = {cat: 0.0 for cat in SAFE_LIMITS}
    for entry in st.session_state.emission_log:
        if str(entry["Year"]) == str(selected_year) and entry["Month"] == selected_month:
            if entry["Factor"] in category_totals:
                category_totals[entry["Factor"]] += abs(entry["Emission"])

    # Gauge Display
    cols = st.columns(3)
    for idx, (category, emission) in enumerate(category_totals.items()):
        with cols[idx % 3]:
            gauge = plot_gauge(emission, category, SAFE_LIMITS[category])
            st.pyplot(gauge)

            if emission <= SAFE_LIMITS[category]:
                st.success(f"**Good!** {category} emissions within limits")
            else:
                excess = emission - SAFE_LIMITS[category]
                st.error(f"**Reduce {excess/1000:.1f} tons** of {category} emissions")


    pass

elif menu == "Emission Analysis":
    # select year, month, facility → pull entries & show breakdown, table, charts
        emissions = {
        "Fossil Fuels": float(st.session_state.get("Fossil Fuels Emission", 0.0)),
        "Fugitive": float(st.session_state.get("Fugitive Emission", 0.0)),
        "Electricity": float(st.session_state.get("Electricity Emission", 0.0)),
        "Water": float(st.session_state.get("Water Emission", 0.0)),
        "Waste": float(st.session_state.get("Waste Emission", 0.0)),
        "Travel": float(st.session_state.get("Travel Emission", 0.0)),
    }

    offset = float(st.session_state.get("Offset Emission", 0.0))
    total_emission = sum(emissions.values())
    net_emission = total_emission - offset

    st.subheader("Emissions Breakdown")
    for category, value in emissions.items():
        st.write(f"**{category}:** {value:.2f} kg CO₂e")

    st.subheader("Total Emission (before offset)")
    st.write(f"**{total_emission:.2f} kg CO₂e**")

    st.subheader("Offset")
    st.write(f"**{offset:.2f} kg CO₂e**")

    st.subheader("Net Emission")
    st.success(f"**{net_emission:.2f} kg CO₂e**")

    st.markdown("<hr style='border-top: 1px dotted #bbb;'>", unsafe_allow_html=True)

    df = pd.DataFrame({
        "Category": list(emissions.keys()),
        "Emissions (kg CO₂)": list(emissions.values())
    })

# Create visualizations
    st.markdown("<hr style='border-top: 1px dotted #bbb;'>", unsafe_allow_html=True)
        categories = ["Fossil Fuels", "Fugitive", "Electricity", "Water", "Waste", "Travel"]
    values = df["Emissions (kg CO₂)"]

    categories = list(emissions.keys())
    values = list(emissions.values())

    df = pd.DataFrame({"Category": categories, "Emissions (kg CO₂)": values})
    st.dataframe(df)

    total = df["Emissions (kg CO₂)"].sum()
    st.subheader(f"Total Carbon Footprint: {total:.2f} kg CO₂")

    color_map = {
        "Fossil Fuels": "#1f77b4",
        "Fugitive": "#ff7f0e",
        "Electricity": "#2ca02c",
        "Water": "#d62728",
        "Waste": "#9467bd",
        "Travel": "#8c564b",
    }


    st.markdown("<hr style='border-top: 1px dotted #bbb;'>", unsafe_allow_html=True)
# Bar Cha
    df["Color"] = df["Category"].map(color_map)

    fig_emissions = px.bar(
        df,
        x="Category",
        y="Emissions (kg CO₂)",
        title="<b>Emissions by Category</b>",
        color="Category",
        color_discrete_map=color_map,
        template="plotly_white"
    )

    fig_emissions.update_layout(
        xaxis=dict(tickmode="linear"),
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=False)
    )

    st.plotly_chart(fig_emissions, use_container_width=True)


    st.markdown("<hr style='border-top: 1px dotted #bbb;'>", unsafe_allow_html=True)
# Pie Chart (only non-negative values)
    pull_values = [0.1 if val < total_emission * 0.1 else 0 for val in df["Emissions (kg CO₂)"]]

# Plot
    st.subheader("🥧 Emissions Pie Chart (Clear & Distinct)")
    fig = px.pie(
    df,
    values="Emissions (kg CO₂)",
    names="Category",
    title="Emission Contribution by Category",
    color_discrete_sequence=px.colors.qualitative.Set3,
    hole=0.4
)
    fig.update_traces(
    textinfo='percent+label',
    pull=pull_values,
    rotation=90,  # rotate for better label spacing
    textfont_size=14
)
    st.plotly_chart(fig)

    st.markdown("<hr style='border-top: 1px dotted #bbb;'>", unsafe_allow_html=True)
    total = df["Emissions (kg CO₂)"].sum()
    st.markdown(f"## **Total Net Emissions: {total:.2f} kg CO₂**")

    st.markdown("<hr style='border-top: 1px dotted #bbb;'>", unsafe_allow_html=True)

# Constants
    TREE_OFFSET_FACTOR = 21            # kg CO₂/year per tree
    LAND_OFFSET_FACTOR = 0.6178         # kg CO₂/year per acre (trees planted)
    GRASS_OFFSET_FACTOR = 0.3707        # kg CO₂/year per acre (approximate)
    WATER_OFFSET_FACTOR = 0.4943      # kg CO₂/year per acre (approximate)

    trees_count7 = st.session_state.get("trees_count7", 0)
    soil_area7 = st.session_state.get("soil_area7", 0)
    water_consum7 = st.session_state.get("water_consum7", 0)
    grass_area7 = st.session_state.get("grass_area7", 0)




# Calculations
    tree_offset = trees_count7 * TREE_OFFSET_FACTOR
    land_offset = soil_area7 * LAND_OFFSET_FACTOR
    grass_offset = grass_area7 * GRASS_OFFSET_FACTOR
    water_offset = water_consum7 * WATER_OFFSET_FACTOR

    total_offset = tree_offset + land_offset + grass_offset + water_offset

# Display
    st.subheader("Offset Contribution Summary")
    st.markdown(f"""
   🌳 You planted **{trees_count7} trees**, used:
    - **{soil_area7:.2f} m^2** for tree planting
    - **{grass_area7:.2f} m^2** covered in grass
    - **{water_consum7:.2f} m^2** covered in water

    ✅ This helped you reduce approximately:
    - **{tree_offset:.2f} kg CO₂/year** via trees
    - **{land_offset:.2f} kg CO₂/year** from tree-planted land
    - **{grass_offset:.2f} kg CO₂/year** from grassy land
    - **{water_offset:.2f} kg CO₂/year** from water-covered area

    💚 **Total Estimated Offset:** **{total_offset:.2f} kg CO₂/year**
     """)


    pass

elif menu == "Year & Month Analysis":
    # compare multiple years or facilities
        if st.session_state.emission_log:
        df_ch = pd.DataFrame(st.session_state.emission_log)

        years_input = st.text_input("Compare Years (comma-separated)", "2022,2023")
        selected_years = [y.strip() for y in years_input.split(",") if y.strip()]
        df_ch = df_ch[df_ch["Year"].isin(selected_years)]

        # Month-wise
        monthwise = df_ch.groupby(["Year", "Month"]).sum().reset_index()
        fig1 = px.line(monthwise, x="Month", y="Emission", color="Year", markers=True,
                       title="<b>Month-wise Emission</b>")
        st.plotly_chart(fig1, use_container_width=True)

        # Facility-wise
        facwise = df_ch.groupby(["Year", "Facility", "Factor"]).sum().reset_index()
        fig2 = px.bar(facwise, x="Facility", y="Emission", color="Factor", facet_col="Year",
                      barmode="group", title="<b>Facility-wise Emission by Factor</b>")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No emissions logged yet. Complete inputs in previous sections.")

    st.markdown("<hr style='border-top: 1px dotted #bbb;'>", unsafe_allow_html=True)

    st.subheader("Download Reports")

    df_log = pd.DataFrame(st.session_state.emission_log)
    csv = df_log.to_csv(index=False).encode('utf-8')

    pass

elif menu == "Download":
    # build a DataFrame from user.emissions
    # st.download_button for CSV
    # zip charts if needed
        # 2. Charts Download (All Visualizations)
    if 'chart_buffers' not in st.session_state:
        st.session_state.chart_buffers = []

    # Collect all figures
    chart_buffers = []

    # Save Gauge Charts
    for idx, (category, emission) in enumerate(category_totals.items()):
        fig = plot_gauge(emission, category, SAFE_LIMITS[category])
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        chart_buffers.append((f"gauge_{category}.png", buf.getvalue()))
        plt.close(fig)

    # Save Plotly Charts
    plotly_figs = [fig_emissions, fig, fig1, fig2]  # Add all figures
    plotly_names = [
        "emissions_bar_chart.png",
        "emissions_pie_chart.png",
        "monthly_trend.png",
        "facility_breakdown.png"
    ]

    for fig, name in zip(plotly_figs, plotly_names):
        buf = io.BytesIO()
        buf.write(to_image(fig, format='png'))
        chart_buffers.append((name, buf.getvalue()))

    # Create ZIP file
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w') as zf:
        # Add CSV
        zf.writestr("emission_data.csv", csv.decode('utf-8'))
        # Add Charts
        for name, data in chart_buffers:
            zf.writestr(name, data)

    zip_buf.seek(0)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Download CSV Report",
            data=csv,
            file_name="carbon_footprint.csv",
            mime="text/csv"
        )

    with col2:
        st.download_button(
            label="📦 Download Full Report (ZIP)",
            data=zip_buf.getvalue(),
            file_name="carbon_footprint_report.zip",
            mime="application/zip"
        )


    st.markdown("<hr style='border-top: 1px dotted #bbb;'>", unsafe_allow_html=True)

    pass
