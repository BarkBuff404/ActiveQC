from src.components.ingestion import fetch_all_data
from src.components.processing import compute_metrics
from src.components.fetch_output import write_outputs
from src.utils.logger import logging
from src.utils.exception import CustomException
import sys

def run_daily_pipeline():
    """
        Main function to run the daily ETL pipeline.
        This function orchestrates the data fetching, processing, and output writing. It is intended to be run as a scheduled task.
    """
    try:
        logging.info("Scheduled ETL run started.")
        raw_data = fetch_all_data()
        metrics_df, summary = compute_metrics(raw_data)
        write_outputs(metrics_df, summary)
        logging.info("Scheduled ETL run completed successfully.")
    except Exception as e:
        err = CustomException(e, sys)
        logging.error(str(err))
        raise err

if __name__ == "__main__":
    run_daily_pipeline()
