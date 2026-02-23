import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE CONFIG MUST BE FIRST ---
st.set_page_config(page_title="FDA Neuro-Watchdog V2", layout="wide")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    df = pd.read_csv('cleaned_fda_data.csv')
    
    # Fix the immortal patients: Convert days to years for anything over 130
    df.loc[df['Patient Age'] > 130, 'Patient Age'] = df['Patient Age'] / 365
    df['Patient Age'] = df['Patient Age'].astype(int)
    
    return df

df_clean = load_data()

# --- SIDEBAR & FILTERING ---
st.sidebar.title("About this Tool")
st.sidebar.info(
    "**FDA Neuro-Watchdog**\n\n"
    "This executive dashboard pulls post-market surveillance data directly from the "
    "openFDA API. It is designed to identify real-world safety signals and quantify "
    "patient risk for neuro-pharmaceuticals."
)

st.sidebar.header("Data Filters")
min_age = int(df_clean['Patient Age'].min())
max_age = int(df_clean['Patient Age'].max())

# Age Slider
age_range = st.sidebar.slider(
    "Filter by Patient Age",
    min_value=min_age,
    max_value=max_age,
    value=(min_age, max_age)
)

# Apply the filter
df_filtered = df_clean[
    (df_clean['Patient Age'] >= age_range[0]) & 
    (df_clean['Patient Age'] <= age_range[1])
]

# --- MAIN PAGE HEADER ---
st.title("FDA Post-Market Surveillance Dashboard")
st.subheader("Target Drug: Donepezil (Aricept)")

# --- DYNAMIC CALCULATIONS ---
total_reports = len(df_filtered)

if total_reports > 0:
    # Recalculate Top Reactions based on the filtered age range
    reactions_series = df_filtered['Adverse Reactions'].astype(str).str.split(', ').explode().str.strip()
    top_reactions = reactions_series.value_counts().head(10).reset_index()
    top_reactions['Count'] = pd.to_numeric(top_reactions['Count'])
    top_reactions.columns = ['Reaction', 'Count']
    top_event = top_reactions['Reaction'].iloc[0] if not top_reactions.empty else "N/A"

    # Calculate Mortality Rate
    death_count = reactions_series[reactions_series.str.lower() == 'death'].count()
    mortality_rate = (death_count / total_reports) * 100
else:
    top_reactions = pd.DataFrame(columns=['Reaction', 'Count'])
    top_event = "N/A"
    mortality_rate = 0.0

# --- EXECUTIVE METRICS ---
col1, col2, col3 = st.columns(3)
col1.metric("Total Valid Reports", total_reports)
col2.metric("Most Frequent Event", top_event)

# Custom styling for Mortality Rate threshold
if mortality_rate > 5.0:
    col3.markdown(
        f"**Mortality Rate**<br><span style='color:#E74C3C; font-size: 32px; font-weight: bold;'>{mortality_rate:.1f}%</span>", 
        unsafe_allow_html=True
    )
else:
    col3.metric("Mortality Rate", f"{mortality_rate:.1f}%")

st.divider()

# --- VISUALIZATIONS ---
if total_reports > 0:
    # Top 10 Reactions Bar Chart
    st.write("### Top 10 Reported Adverse Events")
    fig_bar = px.bar(
        top_reactions, 
        x='Count', 
        y='Reaction', 
        orientation='h',
        color_discrete_sequence=['#2E86C1']
    )
    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_bar, use_container_width=True)

    # Demographics: 2 Columns
    st.write("### Clinical Demographics")
    dem_col1, dem_col2 = st.columns(2)

    with dem_col1:
        fig_donut = px.pie(
            df_filtered, 
            names='Patient Sex', 
            hole=0.4, 
            title='Breakdown by Sex',
            color_discrete_sequence=['#3498DB', '#9B59B6', '#95A5A6']
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with dem_col2:
        fig_hist = px.histogram(
            df_filtered, 
            x='Patient Age', 
            nbins=15, 
            title='Age Distribution',
            color_discrete_sequence=['#28B463']
        )
        fig_hist.update_layout(xaxis_title="Age", yaxis_title="Count")
        st.plotly_chart(fig_hist, use_container_width=True)
else:
    st.warning("No data available for the selected age range.")

# --- DATA TABLE ---
with st.expander("View Filtered Data Source"):
    st.dataframe(df_filtered)
