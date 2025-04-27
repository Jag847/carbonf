# app.py
import streamlit as st
from auth import login
from database import init_db, Session, User, Emission
from datetime import date
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.io as pio
import io, zipfile

FACILITIES = [
    "Residential Areas",
    "Hostels",
    "Academic Area",
    "Health Centre",
    "Schools",
    "Visitor's Hostel",
    "Servants Quarters",
    "Shops/Bank/PO"
]
MONTHS = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

# 1. Initialize DB
init_db()

# 2. Authentication
if not st.session_state.get("logged_in", False):
    login()
    st.stop()


# 3. Greeting & "Let’s get started" button
name = st.session_state.get("username", "")
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
    "Download",
    "Offset Contribution"
])

# 5. Get DB session & current user
db = Session()
user = db.query(User).filter_by(name=name).first()

# Emission factor dictionaries
emission_factors = {
    "Fossil Fuels": {"CNG": 2.21},
    "Fossil Fuels per litre": {"Petrol/Gasoline": 2.315, "Diesel": 2.68, "LPG": 1.51},
    "Fossil Fuels per scm": {"PNG": 2.1},
    "Electricity": {"Coal/Thermal": 0.85, "Solar": 0.00}
}
f_e_f = {
    "Domestic Refrigeration": 1430,
    "Commercial Refrigeration": 3922,
    "Industrial Refrigeration": 2088,
    "Residential and Commercial A/C": 1650
}
of_e_f = {
    "tree": 1.75,
    "soil": 0.0515,
    "grass": 0.0309,
    "water": 0.0412
}
e_e_f = {
    "Coal/Thermal": 0.92,
    "Solar": 0.05
}
w_e_f = 0.344
wa_e_f = {
    "Household Residue": {"Landfills": 1.0, "Combustion": 0.7, "Recycling": 0.2, "Composting": 0.1},
    "Food and Drink Waste": {"Landfills": 1.9, "Combustion": 0.8, "Recycling": 0.3, "Composting": 0.05},
    "Garden Waste": {"Landfills": 0.6, "Combustion": 0.4, "Recycling": 0.2, "Composting": 0.03},
    "Commercial and Industrial Waste": {"Landfills": 2.0, "Combustion": 1.5, "Recycling": 0.6, "Composting": 0.2}
}
SAFE_LIMITS = {
    "Fossil Fuels": 5000,
    "Fugitive": 3000,
    "Electricity": 4000,
    "Water": 2000,
    "Waste": 1500,
    "Travel": 3500
}
def log_emission(category, facility, year, month, value):
    entry = Emission(
        user_id=user.id,
        date=date(int(year), MONTHS.index(month)+1, 1),
        facility=facility,
        category=category,
        value=value
    )
    db.add(entry)
    db.commit()

def plot_gauge(current_value, category, safe_limit):
    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw={'projection': 'polar'})
    ax.set_theta_offset(np.pi/2)
    ax.set_theta_direction(-1)
    # Dynamic scaling with 25% buffer
    max_limit = safe_limit * 1.25
    display_value = min(current_value, max_limit)
    # Angle calculations
    theta_max = 0.75 * np.pi  # 135 degrees
    theta_min = -theta_max    # -135 degrees
    total_range = theta_max - theta_min  # 270 degrees
    # Calculate angles
    safe_angle = (safe_limit / max_limit) * total_range
    excess_angle = ((display_value - safe_limit) / max_limit) * total_range if current_value > safe_limit else 0
    # Background arc (full range)
    ax.barh(1, total_range, height=0.4, left=theta_min, color='#f0f0f0', alpha=0.3)
    # Safe zone (green)
    ax.barh(1, safe_angle, height=0.4, left=theta_min, color='#2ecc71', alpha=0.7)
    # Excess zone (red)
    if current_value > safe_limit:
        ax.barh(1, excess_angle, height=0.4, left=theta_min + safe_angle, color='#e74c3c', alpha=0.7)
    # Needle
    needle_angle = theta_min + (display_value / max_limit) * total_range
    ax.plot([needle_angle, needle_angle], [0, 1.2], color='#2c3e50', lw=2.5)
    # Arc labels
    label_values = [0, safe_limit, max_limit]
    label_angles = [theta_min + (v / max_limit) * total_range for v in label_values]
    ax.set_xticks(label_angles)
    ax.set_xticklabels([f'{v/1000:.0f}k' if v < 10000 else f'{v/1000:.1f}k' for v in label_values],
                       color='#666', fontsize=10)
    # Center text
    plt.text(0, 0, f'{current_value/1000:.1f}k\nCO₂', ha='center', va='center',
             fontsize=14, color='#2c3e50', fontweight='bold')
    # Styling
    ax.set_yticks([])
    ax.spines[:].set_visible(False)
    plt.title(category, pad=20, fontsize=14, color='#2c3e50', fontweight='bold')
    plt.tight_layout()
    return fig

# Initialize session state for emissions log
if "emission_log" not in st.session_state:
    st.session_state.emission_log = []

# 6. Handle each menu choice
if menu == "Carbon Data":
    # Header for Carbon Data
    st.header("Enter Carbon Data")
    # Common inputs
    facility = st.selectbox("Facility", ["Choose Facility"] + FACILITIES)
    month = st.selectbox("Month", ["Choose Month"] + MONTHS)
    year = st.number_input("Year", min_value=0, format="%d", value=date.today().year)

    # Fossil Fuels
    with st.expander("Fossil Fuels"):
        st.subheader("Fossil Fuel Emissions")
        with st.form("fossil_form"):
            fuel_type = st.selectbox("Fuel Type", ["Choose Fuel Type", "CNG", "Petrol/Gasoline", "Diesel", "PNG", "LPG"])
            unit = st.selectbox("Unit", ["Choose Unit", "Kg", "Tonne", "litre", "SCM"])
            amount_consumed = st.number_input("Amount Consumed", min_value=0.0, format="%f")
            submitted = st.form_submit_button("Submit Fossil Fuels Data")
        if submitted:
            if facility == "Choose Facility" or month == "Choose Month":
                st.warning("Please select facility and month.")
            elif fuel_type == "Choose Fuel Type" or unit == "Choose Unit":
                st.warning("Please select fuel type and unit.")
            else:
                factor = None
                amt = amount_consumed
                if unit == "Tonne":
                    amt *= 1000  # convert to kg
                    factor = emission_factors["Fossil Fuels"].get(fuel_type)
                elif unit == "litre":
                    factor = emission_factors["Fossil Fuels per litre"].get(fuel_type)
                elif unit == "SCM":
                    factor = emission_factors["Fossil Fuels per scm"].get(fuel_type)
                elif unit == "Kg":
                    factor = emission_factors["Fossil Fuels"].get(fuel_type)
                if factor is not None:
                    carbon_footprint = amt * factor
                    st.success(f"Your estimated CO₂ emission: **{carbon_footprint:.2f} kg**")
                    st.session_state["Fossil Fuels Emission"] = carbon_footprint
                    if facility != "Choose Facility" and month != "Choose Month":
                        log_emission("Fossil Fuels", facility, year, month, carbon_footprint)
                        st.session_state.emission_log.append({
                            "Year": year,
                            "Month": month,
                            "Facility": facility,
                            "Factor": "Fossil Fuels",
                            "Emission": carbon_footprint
                        })

    # Fugitive
    with st.expander("Fugitive"):
        st.subheader("Fugitive Emissions")
        with st.form("fugitive_form"):
            application_type = st.selectbox("Application Type", ["Choose Application Type"] + list(f_e_f.keys()))
            unit2 = st.selectbox("Unit", ["Choose Unit", "Kg", "Tonne"])
            amt2 = st.number_input("Number of Units", min_value=0.0, format="%f")
            submitted2 = st.form_submit_button("Submit Fugitive Data")
        if submitted2:
            if facility == "Choose Facility" or month == "Choose Month":
                st.warning("Please select facility and month.")
            elif application_type == "Choose Application Type":
                st.warning("Please select an application type.")
            else:
                gwp_factor = f_e_f.get(application_type, 0)
                units_consumed = amt2
                if unit2 == "Tonne":
                    units_consumed *= 1000  # Convert to kg
                fugitive_emission = units_consumed * gwp_factor
                st.success(f"Your estimated CO₂ equivalent emission: **{fugitive_emission:.2f} kg**")
                st.session_state["Fugitive Emission"] = fugitive_emission
                if facility != "Choose Facility" and month != "Choose Month":
                    log_emission("Fugitive", facility, year, month, fugitive_emission)
                    st.session_state.emission_log.append({
                        "Year": year,
                        "Month": month,
                        "Facility": facility,
                        "Factor": "Fugitive",
                        "Emission": fugitive_emission
                    })

    # Electricity
    with st.expander("Electricity"):
        st.subheader("Electricity Emissions")
        with st.form("electricity_form"):
            electricity_type = st.selectbox("Electricity Type", ["Choose electricity Type", "Coal/Thermal", "Solar"])
            electricity_source = st.selectbox("Electricity Source", ["Choose Electricity Source", "Purchased", "Self-Produced"])
            unit3 = st.selectbox("Unit", ["Choose Unit", "KWH"])
            amt3 = st.number_input("Amount Consumed (kWh)", min_value=0.0, format="%f")
            submitted3 = st.form_submit_button("Submit Electricity Data")
        if submitted3:
            if facility == "Choose Facility" or month == "Choose Month":
                st.warning("Please select facility and month.")
            elif electricity_type == "Choose electricity Type":
                st.warning("Please select electricity type.")
            else:
                emission_factor = e_e_f.get(electricity_type, 0)
                electricity_emission = amt3 * emission_factor
                st.success(f"Your estimated CO₂ equivalent emission: **{electricity_emission:.2f} kg**")
                st.session_state["Electricity Emission"] = electricity_emission
                if facility != "Choose Facility" and month != "Choose Month":
                    log_emission("Electricity", facility, year, month, electricity_emission)
                    st.session_state.emission_log.append({
                        "Year": year,
                        "Month": month,
                        "Facility": facility,
                        "Factor": "Electricity",
                        "Emission": electricity_emission
                    })

    # Water
    with st.expander("Water"):
        st.subheader("Water Emissions")
        with st.form("water_form"):
            water_type = st.selectbox("Water Type", ["Choose Water Type", "Supplied Water", "Treated water"])
            discharge_site = st.text_input("Discharge Site")
            unit4 = st.selectbox("Unit", ["Choose Unit", "Cubic metre", "million litres"])
            amt4 = st.number_input("Amount", min_value=0.0, format="%f")
            submitted4 = st.form_submit_button("Submit Water Data")
        if submitted4:
            if facility == "Choose Facility" or month == "Choose Month":
                st.warning("Please select facility and month.")
            else:
                water_emission = 0.0
                if unit4 == "Cubic metre":
                    water_emission = amt4 * w_e_f
                elif unit4 == "million litres":
                    water_emission = amt4 * 1000 * w_e_f
                st.success(f"Your estimated CO₂ equivalent emission from water usage is: **{water_emission:.2f} kg**")
                st.session_state["Water Emission"] = water_emission
                if facility != "Choose Facility" and month != "Choose Month":
                    log_emission("Water", facility, year, month, water_emission)
                    st.session_state.emission_log.append({
                        "Year": year,
                        "Month": month,
                        "Facility": facility,
                        "Factor": "Water",
                        "Emission": water_emission
                    })

    # Waste
    with st.expander("Waste"):
        st.subheader("Waste Emissions")
        with st.form("waste_form"):
            waste_type = st.selectbox("Waste Type", ["Choose Waste Type", "Household Residue",
                                                     "Food and Drink Waste", "Garden Waste", "Commercial and Industrial Waste"])
            treatment_type = st.selectbox("Treatment Type", ["Choose Treatment Type", "Landfills", "Combustion", "Recycling", "Composting"])
            unit5 = st.selectbox("Unit", ["Choose Unit", "Kg", "Tonne"])
            amt5 = st.number_input("Amount", min_value=0.0, format="%f")
            submitted5 = st.form_submit_button("Submit Waste Data")
        if submitted5:
            if facility == "Choose Facility" or month == "Choose Month":
                st.warning("Please select facility and month.")
            elif waste_type == "Choose Waste Type" or treatment_type == "Choose Treatment Type":
                st.warning("Please select waste type and treatment type.")
            else:
                emission_factor = wa_e_f.get(waste_type, {}).get(treatment_type, 0)
                amount_kg = amt5
                if unit5 == "Tonne":
                    amount_kg = amt5 * 1000
                waste_emission = amount_kg * emission_factor
                st.success(f"Your estimated CO₂ equivalent emission from waste is: **{waste_emission:.2f} kg**")
                st.session_state["Waste Emission"] = waste_emission
                if facility != "Choose Facility" and month != "Choose Month":
                    log_emission("Waste", facility, year, month, waste_emission)
                    st.session_state.emission_log.append({
                        "Year": year,
                        "Month": month,
                        "Facility": facility,
                        "Factor": "Waste",
                        "Emission": waste_emission
                    })

    # Travel
    with st.expander("Travel"):
        st.subheader("Travel Emissions")
        with st.form("travel_form"):
            travel_mode = st.selectbox("Mode of Transport", ["Choose Mode of Transport", "Airways", "Roadways", "Railways"])
            emission = 0.0
            flight_emissions = {"Short Haul": 0.15, "Long Haul": 0.11, "Domestic": 0.18, "International": 0.13}
            train_emission_factors = {"Electric": 0.035, "Diesel": 0.06, "Hydrogen": 0.04}
            personal_emission_factors = {"Small Sized Car": 0.12, "Medium Sized Car": 0.17, "Large Sized Car": 0.22, "Motorcycle": 0.09}
            bus_emission_factors = {"Electricity": 0.03, "Diesel": 0.09, "Hydrogen": 0.05}
            taxi_emission_factors = {"Electricity": 0.06, "Petrol": 0.16, "Hydrogen": 0.07, "CNG": 0.13}

            if travel_mode == "Airways":
                flight_length = st.selectbox("Flight Length", ["Short Haul", "Long Haul", "Domestic", "International"])
                distance = st.number_input("Enter distance traveled (km)", min_value=0.0, step=1.0)
                if distance:
                    emission = distance * flight_emissions.get(flight_length, 0)
            elif travel_mode == "Railways":
                rail_type = st.selectbox("Rail Type", ["Metro", "National Railways"])
                if rail_type == "Metro":
                    distance = st.number_input("Enter distance traveled (km)", min_value=0.0, step=1.0)
                    if distance:
                        emission = distance * 0.04
                elif rail_type == "National Railways":
                    train_type = st.selectbox("Train Type", ["Electric", "Diesel", "Hydrogen"])
                    distance = st.number_input("Enter distance traveled (km)", min_value=0.0, step=1.0)
                    if distance:
                        emission = distance * train_emission_factors.get(train_type, 0)
            elif travel_mode == "Roadways":
                ownership = st.selectbox("Vehicle Ownership", ["Public", "Personal"])
                if ownership == "Personal":
                    vehicle_type = st.selectbox("Vehicle Type", ["Small Sized Car", "Medium Sized Car", "Large Sized Car", "Motorcycle"])
                    distance = st.number_input("Enter distance traveled (km)", min_value=0.0, step=1.0)
                    if distance:
                        emission = distance * personal_emission_factors.get(vehicle_type, 0)
                elif ownership == "Public":
                    vehicle_type = st.selectbox("Vehicle Type", ["Bus", "Taxi"])
                    if vehicle_type == "Bus":
                        bus_fuel = st.selectbox("Bus Runs On", ["Electricity", "Diesel", "Hydrogen"])
                        distance = st.number_input("Enter distance traveled (km)", min_value=0.0, step=1.0)
                        if distance:
                            emission = distance * bus_emission_factors.get(bus_fuel, 0)
                    elif vehicle_type == "Taxi":
                        taxi_fuel = st.selectbox("Taxi Runs On", ["Electricity", "Petrol", "Hydrogen", "CNG"])
                        distance = st.number_input("Enter distance traveled (km)", min_value=0.0, step=1.0)
                        if distance:
                            emission = distance * taxi_emission_factors.get(taxi_fuel, 0)
            submitted6 = st.form_submit_button("Submit Travel Data")
        if submitted6:
            if facility == "Choose Facility" or month == "Choose Month":
                st.warning("Please select facility and month.")
            elif travel_mode == "Choose Mode of Transport":
                st.warning("Please select a mode of transport.")
            else:
                st.success(f"Your estimated CO₂ emission from travel is: **{emission:.2f} kg**")
                st.session_state["Travel Emission"] = emission
                if facility != "Choose Facility" and month != "Choose Month":
                    log_emission("Travel", facility, year, month, emission)
                    st.session_state.emission_log.append({
                        "Year": year,
                        "Month": month,
                        "Facility": facility,
                        "Factor": "Travel",
                        "Emission": emission
                    })
elif menu == "Carbon Metre":
    st.header("Carbon Footprint Summary")
    # Year/Month Filter
    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.selectbox("Select Year", reversed(["2024","2023","2022","2021","2020","2019","2018","2017","2016","2015"]))
    with col2:
        selected_month = st.selectbox("Select Month", ["January","February","March","April","May","June",
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
elif menu == "Emission Analysis":
    emissions = {
        "Fossil Fuels": float(st.session_state.get("Fossil Fuels Emission", 0.0)),
        "Fugitive": float(st.session_state.get("Fugitive Emission", 0.0)),
        "Electricity": float(st.session_state.get("Electricity Emission", 0.0)),
        "Water": float(st.session_state.get("Water Emission", 0.0)),
        "Waste": float(st.session_state.get("Waste Emission", 0.0)),
        "Travel": float(st.session_state.get("Travel Emission", 0.0))
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

    records = db.query(Emission).filter(Emission.user_id==user.id).all()
    df_all = pd.DataFrame([{"Category": rec.category, "Emissions (kg CO₂)": rec.value} for rec in records])
    if not df_all.empty:
        summary = df_all.groupby("Category").sum().reset_index()
        total = summary["Emissions (kg CO₂)"].sum()
        st.dataframe(summary)
        st.subheader(f"Total Carbon Footprint: {total:.2f} kg CO₂")
        color_map = {
            "Fossil Fuels": "#1f77b4",
            "Fugitive": "#ff7f0e",
            "Electricity": "#2ca02c",
            "Water": "#d62728",
            "Waste": "#9467bd",
            "Travel": "#8c564b",
        }
        # Bar chart
        fig_bar = px.bar(
            summary,
            x="Category",
            y="Emissions (kg CO₂)",
            color="Category",
            color_discrete_map=color_map,
            title="<b>Emissions by Category</b>",
            template="plotly_white"
        )
        fig_bar.update_layout(xaxis=dict(tickmode="linear"), plot_bgcolor="rgba(0,0,0,0)", yaxis=dict(showgrid=False))
        st.plotly_chart(fig_bar, use_container_width=True)
        # Pie chart
        fig_pie = px.pie(
            summary,
            values="Emissions (kg CO₂)",
            names="Category",
            title="Emission Contribution by Category",
            color_discrete_sequence=px.colors.qualitative.Set3,
            hole=0.4
        )
        st.subheader("🥧 Emissions Pie Chart")
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No emissions data to analyze.")

elif menu == "Year and Month Analysis":
    st.header("Year and Month Analysis")
    # Prepare dataframe of records
    records = db.query(Emission).filter(Emission.user_id==user.id).all()
    df_ch = pd.DataFrame([{"Year": rec.date.year, "Month": rec.date.strftime("%B"),
                           "Facility": rec.facility, "Category": rec.category, "Emission": rec.value} for rec in records])
    if not df_ch.empty:
        years_input = st.text_input("Compare Years (comma-separated)", value="")
        selected_years = [int(y.strip()) for y in years_input.split(",") if y.strip().isdigit()]
        if selected_years:
            df_ch = df_ch[df_ch["Year"].isin(selected_years)]
        # Month-wise line chart
        monthwise = df_ch.groupby(["Year","Month"]).sum().reset_index()
        fig1 = px.line(monthwise, x="Month", y="Emission", color="Year", markers=True, title="<b>Month-wise Emission</b>")
        # Order months properly
        month_order = ["January","February","March","April","May","June","July","August","September","October","November","December"]
        fig1.update_xaxes(categoryorder="array", categoryarray=month_order)
        st.plotly_chart(fig1, use_container_width=True)
        # Facility-wise bar chart
        facwise = df_ch.groupby(["Year", "Facility", "Category"]).sum().reset_index()
        fig2 = px.bar(facwise, x="Facility", y="Emission", color="Category", facet_col="Year",
                      barmode="group", title="<b>Facility-wise Emission by Category</b>")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No emissions data to analyze.")

elif menu == "Download":
    st.header("Download Reports")
    # Prepare CSV of all data
    records = db.query(Emission).filter(Emission.user_id==user.id).all()
    df_all = pd.DataFrame([{"Year": rec.date.year, "Month": rec.date.month, "Facility": rec.facility,
                            "Category": rec.category, "Emission": rec.value} for rec in records])
    csv = df_all.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV", data=csv, file_name="emissions.csv", mime="text/csv")
    # Generate charts and zip
    if not df_all.empty:
        # Bar and pie
        summary = df_all.groupby("Category")["Emission"].sum().reset_index()
        fig_bar = px.bar(summary, x="Category", y="Emission", title="Emissions by Category", color="Category", template="plotly_white")
        fig_pie = px.pie(summary, values="Emission", names="Category", title="Emissions Distribution", hole=0.4)
        # Monthly trend
        df_all["MonthName"] = df_all["Month"].apply(lambda m: ["January","February","March","April","May","June","July","August","September","October","November","December"][m-1])
        monthly = df_all.groupby(["Year","MonthName"])["Emission"].sum().reset_index()
        fig1 = px.line(monthly, x="MonthName", y="Emission", color="Year", markers=True, title="Monthly Emission Trend")
        fig1.update_xaxes(categoryorder="array", categoryarray=["January","February","March","April","May","June","July","August","September","October","November","December"])
        # Create ZIP
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr("emissions.csv", csv.decode('utf-8'))
            charts = {"bar_chart.png": fig_bar, "pie_chart.png": fig_pie, "monthly_trend.png": fig1}
            for name, fig in charts.items():
                img_buf = pio.to_image(fig, format='png')
                z.writestr(name, img_buf)
        buf.seek(0)
        st.download_button("📥 Download All Charts and Data (ZIP)", data=buf.getvalue(), file_name="reports.zip", mime="application/zip")
    else:
        st.info("No emissions data to download.")

elif menu == "Offset Contribution":
    st.header("Offset Contribution")
    col1, col2 = st.columns(2)
    with col1:
        facility7 = st.selectbox("Facility", ["Choose Facility"] + FACILITIES)
        year7 = st.number_input("Year", min_value=0, format="%d", value=date.today().year)
        month7 = st.selectbox("Month", ["Choose Month", "January", "February", "March", "April", "May", "June",
                                       "July", "August", "September", "October", "November", "December"])
        water_area = st.number_input("Area Covered Under Water (m²)", min_value=0.0, format="%.2f")
    with col2:
        trees_count7 = st.number_input("Number of Trees", min_value=0, format="%d", key="offset_trees_count"
)
        soil_area7 = st.number_input("Area Covered Under Soil (m²)", min_value=0.0, format="%.2f", key="offset_soil_area")
        grass_area7 = st.number_input("Area Covered Under Grass (m²)", min_value=0.0, format="%.2f", key="offset_grass_area"
))
        water_consum7 = st.number_input("Area Covered Under Water (m²)", min_value=0.0, format="%.2f", key="offset_water_area")

    tree_offset = trees_count7 * of_e_f["tree"]
    soil_offset = soil_area7 * of_e_f["soil"]
    grass_offset = grass_area7 * of_e_f["grass"]
    water_offset = water_consum7 * of_e_f["water"]
    total_offset = tree_offset + soil_offset + grass_offset + water_offset
    # Display
    st.subheader("Offset Contribution Summary")
    st.markdown(f"""
   🌳 You planted **{trees_count7} trees**, used:
    - **{soil_area7:.2f} m^2** for tree planting
    - **{grass_area7:.2f} m^2** covered in grass
    - **{water_consum7:.2f} m^2** covered in water

    ✅ This helped you reduce approximately:
    - **{tree_offset:.2f} kg CO₂/year** via trees
    - **{soil_offset:.2f} kg CO₂/year** from tree-planted land
    - **{grass_offset:.2f} kg CO₂/year** from grassy land
    - **{water_offset:.2f} kg CO₂/year** from water-covered area

    💚 **Total Estimated Offset:** **{total_offset:.2f} kg CO₂/year**
     """)

    
