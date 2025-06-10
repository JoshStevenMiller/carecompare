import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import pgeocode
import streamlit as st
import os

# Define possible file paths for each care type
expected_files = {
    "Skilled Nursing": "FY_2025_SNF_VBP_Facility_Performance.csv",
    "Home Health": "HH_Provider_Apr2025.csv",
    "Inpatient Rehab": "Inpatient_Rehabilitation_Facility-Provider_Data_Mar2025.csv",
    "Long Term Care": "Long-Term_Care_Hospital-Provider_Data_Mar2025.csv",
    "Hospice": "Provider_CAHPS_Hospice_Survey_Data_May2025 (1).csv"
}

performance_columns = {
    "Skilled Nursing": "Performance Score",
    "Home Health": "Quality of patient care star rating",
    "Inpatient Rehab": "Score",
    "Long Term Care": "Score",
    "Hospice": "Score"
}

address_columns = {
    "Skilled Nursing": "ZIP Code",
    "Home Health": "ZIP Code",
    "Inpatient Rehab": "ZIP Code",
    "Long Term Care": "ZIP Code",
    "Hospice": "ZIP Code"
}

def get_user_coords(address):
    geolocator = Nominatim(user_agent="care_compare_app")
    location = geolocator.geocode(address)
    if location:
        return (location.latitude, location.longitude)
    else:
        raise ValueError("Address could not be geocoded.")

def get_zip_centroids(zip_codes):
    nomi = pgeocode.Nominatim('us')
    zip_info = nomi.query_postal_code(zip_codes.tolist())
    zip_coords = zip_info[['postal_code', 'latitude', 'longitude']].dropna()
    zip_coords = zip_coords.set_index('postal_code')
    return zip_coords

def scale_to_five(value, min_val, max_val):
    if pd.isna(value):
        return "N/A"
    return round(1 + 4 * ((value - min_val) / (max_val - min_val)), 2)

def process_dataset(modality, file_path, user_coords):
    try:
        df = pd.read_csv(file_path, dtype=str)
        zip_col = address_columns[modality]

        if modality in ["Hospice", "Long Term Care", "Inpatient Rehab"]:
            df = df[df['Score'].notna() & (df['Score'] != "Not Applicable") & (df['Score'] != "")]
            df['Score'] = pd.to_numeric(df['Score'], errors='coerce')
            df = df.dropna(subset=['Score'])
            df_grouped = df.groupby(['CMS Certification Number (CCN)', zip_col])['Score'].mean().reset_index()
            df_grouped[zip_col] = df_grouped[zip_col].astype(str)
            zip_coords = get_zip_centroids(df_grouped[zip_col].unique())
            df_grouped = df_grouped.merge(zip_coords, left_on=zip_col, right_index=True, how="left")
            df_grouped = df_grouped.dropna(subset=['latitude', 'longitude'])
            df_grouped['Distance (miles)'] = df_grouped.apply(
                lambda row: geodesic(user_coords, (row['latitude'], row['longitude'])).miles,
                axis=1
            )
            local_df = df_grouped[df_grouped['Distance (miles)'] <= 25]
            local_avg = local_df['Score'].mean()
            national_avg = df_grouped['Score'].mean()
            min_score, max_score = df_grouped['Score'].min(), df_grouped['Score'].max()
            return local_avg, national_avg, min_score, max_score

        elif modality == "Home Health":
            rating_col = performance_columns[modality]
            df = df[df[rating_col].notna() & (df[rating_col] != "-")]
            df[rating_col] = pd.to_numeric(df[rating_col], errors='coerce')
            df = df.dropna(subset=[rating_col])
            df[zip_col] = df[zip_col].astype(str)
            zip_coords = get_zip_centroids(df[zip_col].unique())
            df = df.merge(zip_coords, left_on=zip_col, right_index=True, how="left")
            df = df.dropna(subset=['latitude', 'longitude'])
            df['Distance (miles)'] = df.apply(
                lambda row: geodesic(user_coords, (row['latitude'], row['longitude'])).miles,
                axis=1
            )
            local_df = df[df['Distance (miles)'] <= 25]
            local_avg = local_df[rating_col].mean()
            national_avg = df[rating_col].mean()
            min_score, max_score = df[rating_col].min(), df[rating_col].max()
            return local_avg, national_avg, min_score, max_score

        else:
            rating_col = performance_columns[modality]
            df = df[df[rating_col].notna() & (df[rating_col] != "Not Available")]
            df[rating_col] = pd.to_numeric(df[rating_col], errors='coerce')
            df = df[df[rating_col] > 0]
            df[zip_col] = df[zip_col].astype(str)
            zip_coords = get_zip_centroids(df[zip_col].unique())
            df = df.merge(zip_coords, left_on=zip_col, right_index=True, how="left")
            df = df.dropna(subset=['latitude', 'longitude'])
            df['Distance (miles)'] = df.apply(
                lambda row: geodesic(user_coords, (row['latitude'], row['longitude'])).miles,
                axis=1
            )
            local_df = df[df['Distance (miles)'] <= 25]
            local_avg = local_df[rating_col].mean()
            national_avg = df[rating_col].mean()
            min_score, max_score = df[rating_col].min(), df[rating_col].max()
            return local_avg, national_avg, min_score, max_score

    except Exception as e:
        return None, None, None, None

# Streamlit UI
st.title("Healthcare Facility Comparison Tool")
st.write("Compare your local care facilities to national averages across five care types.")

user_address = st.text_input("Enter your address:", "3401 NW 85th Court, Kansas City, MO 64154")

if user_address:
    try:
        user_coords = get_user_coords(user_address)

        results = []
        for modality, filename in expected_files.items():
            if os.path.exists(filename):
                local_avg, national_avg, min_val, max_val = process_dataset(modality, filename, user_coords)
                if local_avg is not None and national_avg is not None:
                    results.append({
                        "Care Type": modality,
                        "Local Avg (25 mi)": round(local_avg, 2),
                        "National Avg": round(national_avg, 2),
                        "Local (1-5 Scale)": scale_to_five(local_avg, min_val, max_val),
                        "National (1-5 Scale)": scale_to_five(national_avg, min_val, max_val)
                    })
                else:
                    results.append({
                        "Care Type": modality,
                        "Local Avg (25 mi)": "N/A",
                        "National Avg": "N/A",
                        "Local (1-5 Scale)": "N/A",
                        "National (1-5 Scale)": "N/A"
                    })
            else:
                results.append({
                    "Care Type": modality,
                    "Local Avg (25 mi)": "Missing File",
                    "National Avg": "Missing File",
                    "Local (1-5 Scale)": "Missing File",
                    "National (1-5 Scale)": "Missing File"
                })

        st.subheader("Comparison Summary")
        st.dataframe(pd.DataFrame(results))

    except Exception as e:
        st.error(f"Error: {e}")