import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
import math

st.set_page_config(
    page_title="Pakistan Rainwater Harvesting Guide",
    page_icon="💧",
    layout="wide"
)

@st.cache_data
def load_data():
    rainfall = pd.read_csv("data/pakistan_chirps_1995_2024_rainfall_summary.csv")
    landcover = pd.read_csv("data/pakistan_dynamic_world_built_percent_5km2.csv")

    rainfall = rainfall.dropna(subset=["lat", "lon"])
    landcover = landcover.dropna(subset=["lat", "lon"])

    rainfall_tree = cKDTree(rainfall[["lat", "lon"]].to_numpy())
    landcover_tree = cKDTree(landcover[["lat", "lon"]].to_numpy())

    return rainfall, landcover, rainfall_tree, landcover_tree


def get_marla_size_sqft(city):
    small_marla_cities = ["Islamabad", "Rawalpindi", "Lahore", "Peshawar"]
    return 225 if city in small_marla_cities else 275


def estimate_roof_area(city, house_marla):
    marla_size = get_marla_size_sqft(city)
    plot_area = house_marla * marla_size
    roof_area = plot_area * 0.70
    return marla_size, plot_area, roof_area


def runoff_litres(roof_area_sqft, rainfall_mm):
    return roof_area_sqft * 0.092903 * rainfall_mm * 0.80


def round_tank_size(litres):
    if litres <= 500:
        return 500
    if litres <= 1000:
        return 1000
    if litres <= 2000:
        return 2000
    if litres <= 3000:
        return 3000
    if litres <= 5000:
        return 5000
    if litres <= 7500:
        return 7500
    if litres <= 10000:
        return 10000
    return math.ceil(litres / 5000) * 5000


rainfall, landcover, rainfall_tree, landcover_tree = load_data()

st.title("💧 Pakistan Rainwater Harvesting Guide")
st.write(
    "Estimate roof runoff, tank size, and groundwater recharge need using "
    "CHIRPS rainfall and Dynamic World land-cover data."
)

with st.sidebar:
    st.header("Enter your property details")

    city = st.selectbox(
        "City",
        [
            "Islamabad",
            "Rawalpindi",
            "Lahore",
            "Peshawar",
            "Karachi",
            "Quetta",
            "Multan",
            "Faisalabad",
            "Other"
        ]
    )

    house_marla = st.number_input(
        "House size in marla",
        min_value=1.0,
        max_value=100.0,
        value=10.0,
        step=0.5
    )

    st.subheader("Location")
    lat = st.number_input(
        "Latitude",
        value=33.6844,
        format="%.6f"
    )

    lng = st.number_input(
        "Longitude",
        value=73.0479,
        format="%.6f"
    )

    calculate = st.button("Calculate")

if calculate:
    rainfall_distance, rainfall_idx = rainfall_tree.query([[lat, lng]], k=1)
    landcover_distance, landcover_idx = landcover_tree.query([[lat, lng]], k=1)

    r = rainfall.iloc[int(rainfall_idx[0])]
    l = landcover.iloc[int(landcover_idx[0])]

    marla_size, plot_area, roof_area = estimate_roof_area(city, house_marla)

    annual_rainfall = float(r["avg_annual_rainfall_mm"])
    annual_runoff = runoff_litres(roof_area, annual_rainfall)

    built_percent = float(l["built_percent_5km2"])
    pervious_percent = float(l["pervious_percent_5km2"])
    recharge_recommended = built_percent > 75

    st.subheader("Summary")

    col1, col2, col3 = st.columns(3)

    col1.metric("Estimated roof area", f"{roof_area:,.0f} sq ft")
    col2.metric("Annual rainfall", f"{annual_rainfall:,.0f} mm")
    col3.metric("Annual runoff potential", f"{annual_runoff:,.0f} L")

    st.subheader("Roof estimation")

    st.write({
        "City": city,
        "Marla size used": f"{marla_size} sq ft",
        "Plot area": f"{plot_area:,.0f} sq ft",
        "Roof coverage factor": "70%",
        "Estimated roof area": f"{roof_area:,.0f} sq ft"
    })

    st.subheader("Rainfall event runoff")

    rainfall_events = [25, 50, 75, 100, 125, 150, 175, 200]

    rows = []
    for mm in rainfall_events:
        runoff = runoff_litres(roof_area, mm)
        rows.append({
            "Rainfall event": f"{mm} mm" if mm < 200 else ">200 mm",
            "Harvestable runoff": f"{runoff:,.0f} L",
            "Suggested tank": f"{round_tank_size(runoff * 0.75):,.0f} L"
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    recommended_tank = round_tank_size(runoff_litres(roof_area, 50))

    st.subheader("Tank recommendation")
    st.success(
        f"Recommended starting tank size: {recommended_tank:,.0f} litres. "
        "This is based on approximately a 50 mm rainfall event."
    )

    st.subheader("Monthly rainfall profile")

    monthly = pd.DataFrame({
        "Month": [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ],
        "Average rainfall mm": [
            float(r["avg_jan_rainfall_mm"]),
            float(r["avg_feb_rainfall_mm"]),
            float(r["avg_mar_rainfall_mm"]),
            float(r["avg_apr_rainfall_mm"]),
            float(r["avg_may_rainfall_mm"]),
            float(r["avg_jun_rainfall_mm"]),
            float(r["avg_jul_rainfall_mm"]),
            float(r["avg_aug_rainfall_mm"]),
            float(r["avg_sep_rainfall_mm"]),
            float(r["avg_oct_rainfall_mm"]),
            float(r["avg_nov_rainfall_mm"]),
            float(r["avg_dec_rainfall_mm"])
        ]
    })

    st.bar_chart(monthly.set_index("Month"))

    st.subheader("Built-up / likely impervious area")

    col4, col5 = st.columns(2)
    col4.metric("Built-up / likely impervious", f"{built_percent:.1f}%")
    col5.metric("Pervious area", f"{pervious_percent:.1f}%")

    if recharge_recommended:
        st.warning(
            "Built-up area within the 5 km² neighborhood is above 75%. "
            "Local groundwater recharge should be considered, such as recharge pits, "
            "soakaways, trenches, or permeable paving, after checking soil type, "
            "groundwater depth, contamination risk, and nearby foundations."
        )
    else:
        st.info(
            "Built-up area is below the 75% trigger. Recharge can still be considered "
            "where site conditions are suitable."
        )

    st.subheader("Matched data pixels")

    st.write({
        "Rainfall pixel lat": float(r["lat"]),
        "Rainfall pixel lon": float(r["lon"]),
        "Land-cover pixel lat": float(l["lat"]),
        "Land-cover pixel lon": float(l["lon"])
    })

else:
    st.info("Enter property details and click Calculate.")