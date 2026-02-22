import streamlit as st
import pandas as pd
import altair as alt

# Load Data
df_clean = pd.read_csv('cleaned_fda_data.csv')
df_top = pd.read_csv('top_reactions.csv')

# Configure Page
st.set_page_config(page_title="FDA Neuro-Watchdog", layout="wide")
st.title("FDA Post-Market Surveillance Dashboard")
st.subheader("Target Drug: Donepezil (Aricept)")

# Key Metrics
col1, col2 = st.columns(2)
col1.metric("Total Valid Reports Analyzed", len(df_clean))
col2.metric("Most Frequent Critical Event", df_top['Reaction'].iloc[0])

st.divider()

# Visualization
st.write("### Top 10 Reported Adverse Events")
chart = alt.Chart(df_top).mark_bar(color='#2E86C1').encode(
    x=alt.X('Count:Q', title='Number of Reports'),
    y=alt.Y('Reaction:N', sort='-x', title='Adverse Event')
).properties(height=400)

st.altair_chart(chart, use_container_width=True)

# Data Table
with st.expander("View Cleaned Data Source"):
    st.dataframe(df_clean)
