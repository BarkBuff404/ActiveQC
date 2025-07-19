import streamlit as st # type: ignore
from datetime import datetime, timedelta
import sys

from src.components.ingestion import fetch_all_data
from src.components.processing import compute_metrics
from src.components.fetch_output import write_outputs
from src.utils.logger import logging
from src.utils.exception import CustomException
from src.config.settings import settings

st.set_page_config(layout="wide", page_title="Broke Monitoring Dashboard")
st.title("Broke Monitoring Dashboard")

try:
    logging.info("Manual dashboard ETL execution started.")
    st.info("Running ingestion and processing...")

    raw_data = fetch_all_data()
    metrics_df, summary = compute_metrics(raw_data)
    write_outputs(metrics_df, summary)

    st.success("Data processed successfully.")
except Exception as e:
    err = CustomException(e, sys)
    logging.error(str(err))
    st.error(f"Error: {err}")
    st.stop()

st.write("---")
st.header("Explore Historical Broke Data")

machine_input = st.selectbox("Select Machine", sorted(metrics_df['machine_id'].unique()))

col1, col2 = st.columns(2)
start_date = col1.date_input("Start Date", datetime.now().date() - timedelta(days=30))
end_date = col2.date_input("End Date", datetime.now().date())

filtered = metrics_df[
    (metrics_df['machine_id'] == machine_input) &
    (metrics_df['calculation_date'] >= start_date) &
    (metrics_df['calculation_date'] <= end_date)
]

if filtered.empty:
    st.warning("No data available in the selected range.")
    st.stop()

st.subheader("Summary Metrics")
for col in ['SAP_Production', 'QCS_Production', 'Reel_Production',
            'Rewinder_Input', 'Rewinder_Output', 'Qc_Rejection', 'Handling_Loss']:
    st.metric(col, f"{filtered[col].sum():,.2f} tons")

st.write("---")
st.subheader("Raw Data Table")
st.dataframe(filtered.set_index("calculation_date"))