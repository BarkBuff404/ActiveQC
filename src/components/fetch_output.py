import pandas as pd
import json
import os
from src.config.settings import settings
from src.utils.logger import logging

def write_outputs(df, summary):
    """
        Write the DataFrame and summary to disk.
        Args:
            df (pd.DataFrame): The DataFrame to write.
            summary (dict): The summary dictionary to write.
        Raises: Exception: If writing to disk fails.
    """
    os.makedirs(os.path.dirname(settings.HISTORY_FILE), exist_ok=True)

    if os.path.exists(settings.HISTORY_FILE):
        old_df = pd.read_feather(settings.HISTORY_FILE)
        df = pd.concat([old_df, df], ignore_index=True).drop_duplicates()

    df.to_feather(settings.HISTORY_FILE)

    with open(settings.SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=4)

    logging.info("Data written to feather and JSON summary.")
