import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# --- PAGE CONFIG ---
st.set_page_config(page_title="FDA Neuro-Watchdog V3", layout="wide")

# --- DRUG DATABASE ---
NEURO_DRUGS = [
    "Donepezil",    # Alzheimer's
    "Memantine",    # Alzheimer's
    "Levodopa",     # Parkinson's
    "Lithium",      # Bipolar Disorder
    "Fluoxetine",   # Depression (Prozac)
    "Aripiprazole"  # Schizophrenia / Bipolar (Abilify)
]

# --- API & DATA PROCESSING ENGINE ---
@st.cache_data(show_spinner=False)
def fetch_and_clean_fda_data(drug_name):
    """Fetches live data from openFDA and cleans it on the fly."""
    url = "https://api.fda.gov/drug/event.json"
    search_query = f'patient.drug.medicinalproduct:("{drug_name}")'
    params = {'search': search_query, 'limit': 500}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json().get('results', [])
    except:
        return pd.DataFrame() # Return empty on failure

    # 1. Parse JSON
    parsed_reports = []
    for report in results:
        patient_data = report.get('patient', {})
        reactions_list = patient_data.get('reaction', [])
        reactions = [rx.get('reactionmeddrapt', 'Unknown') for rx in reactions_list]
        
        report_dict = {
            'Date': report.get('receivedate'),
            'Patient Sex': patient_data.get('patientsex'),
            'Patient Age': patient_data.get('patientonsetage'),
            'Seriousness': report.get('seriousness'),
            'Adverse Reactions': ", ".join(reactions)
        }
        parsed_reports.append(report_dict)
        
    df = pd.DataFrame(parsed_reports)
    if df.empty: return df

    # 2. Clean Data
    sex_mapping = {1: 'Male', '1': 'Male', 2: 'Female', '2': 'Female', 0: 'Unknown', '0': 'Unknown'}
    df['Patient Sex'] = df['Patient Sex'].map(sex_mapping).fillna('Unknown')
    
    df['Patient Age'] = pd.to_numeric(df['Patient Age'], errors='coerce')
    df = df.dropna(subset=['Patient Age', 'Adverse Reactions'])
    
    # Fix the immortal patients (convert days to years)
    df['Patient Age'] = df['Patient Age'].astype(float)
    df.loc[df['Patient Age'] > 130, 'Patient Age'] = df['Patient Age'] / 365
    df['Patient Age'] = df['Patient Age'].astype(int)
    
    return df

# --- UI & SIDEBAR ---
st.sidebar.title("Neuro-Watchdog")
st.sidebar.info("Live openFDA API Post-Market Surveillance")

st.sidebar.header("Select Target")
selected_drug = st.sidebar.selectbox("Neuro-Pharmaceutical", NEURO_DRUGS)

# Fetch Data Live
with st.spinner(f"Querying FDA Database for {selected_drug}..."):
    df_clean = fetch_and_clean_fda_data(selected_drug)

if df_clean.empty:
    st.error(f"Failed to pull data for {selected_drug}. The FDA API might be down or rate-limited.")
    st.stop()

# --- FILTERS ---
st.sidebar.header("Demographic Filters")
min_age, max_age = int(df_clean['Patient Age'].min()), int(df_clean['Patient Age'].max())
age_range = st.sidebar.slider("Patient Age", min_age, max_age, (min_age, max_age))

df_filtered = df_clean[(df_clean['Patient Age'] >= age_range[0]) & (df_clean['Patient Age'] <= age_range[1])]
total_reports = len(df_filtered)

# --- MAIN DASHBOARD ---
st.title("Live Pharmaceutical Risk Dashboard")
st.subheader(f"Active Target: {selected_drug}")

if total_reports > 0:
    # Math Engine
    reactions_series = df_filtered['Adverse Reactions'].astype(str).str.split(', ').explode().str.strip()
    top_reactions = reactions_series.value_counts().head(10).reset_index()
    top_reactions.columns = ['Reaction', 'Count']
    top_reactions['Count'] = pd.to_numeric(top_reactions['Count'])
    
    top_event = top_reactions['Reaction'].iloc[0]
    death_count = reactions_series[reactions_series.str.lower() == 'death'].count()
    mortality_rate = (death_count / total_reports) * 100

    # Executive Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Valid Clinical Reports", total_reports)
    col2.metric("Primary Safety Signal", top_event)
    
    if mortality_rate > 5.0:
        col3.markdown(f"**Mortality Rate**<br><span style='color:#E74C3C; font-size: 32px; font-weight: bold;'>{mortality_rate:.1f}%</span>", unsafe_allow_html=True)
    else:
        col3.metric("Mortality Rate", f"{mortality_rate:.1f}%")

    st.divider()

    # Visualizations
    st.write(f"### Top 10 Reported Events: {selected_drug}")
    fig_bar = px.bar(top_reactions, x='Count', y='Reaction', orientation='h', color_discrete_sequence=['#2E86C1'])
    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_bar, use_container_width=True)

    dem_col1, dem_col2 = st.columns(2)
    with dem_col1:
        fig_donut = px.pie(df_filtered, names='Patient Sex', hole=0.4, title='Sex Breakdown', color_discrete_sequence=['#3498DB', '#9B59B6', '#95A5A6'])
        st.plotly_chart(fig_donut, use_container_width=True)
    with dem_col2:
        fig_hist = px.histogram(df_filtered, x='Patient Age', nbins=15, title='Age Distribution', color_discrete_sequence=['#28B463'])
        fig_hist.update_layout(xaxis_title="Age", yaxis_title="Count")
        st.plotly_chart(fig_hist, use_container_width=True)

    with st.expander("View Live JSON Output (Parsed)"):
        st.dataframe(df_filtered)
else:
    st.warning("No data available for the selected demographic.")
