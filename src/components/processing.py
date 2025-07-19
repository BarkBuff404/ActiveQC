import pandas as pd
from src.utils.logger import logging
from src.utils.exception import CustomException
from src.config.settings import settings
import sys

def compute_metrics(data):
    """
    Computes daily and monthly metrics for each machine based on the provided data.
    Args: data (dict): Contains DataFrames for SAP, Rewinder, QC data and PI server connection.
    Returns:
        pd.DataFrame: A DataFrame containing the computed metrics for each machine.
        dict: A summary dictionary with last calculated date and machine-specific metrics.
    """
    try:
        df_list = []

        for machine in settings.PI_TAGS.keys():
            m = {
                "calculation_date": data['date'].date(),
                "machine_id": machine,
                "SAP_Production": round(data['sap_df'][data['sap_df']['machine'] == machine]['MENGE'].sum() / 1000, 2),
                "QCS_Production": 0,
                "Reel_Production": 0,
                "Rewinder_Input": 0,
                "Rewinder_Output": 0,
                "Qc_Rejection": 0,
                "Handling_Loss": 0,
            }

            try:
                if data['pi_server']:
                    qcs_tag, reel_tag = settings.PI_TAGS[machine]
                    m["QCS_Production"] = float(data['pi_server'].search(qcs_tag)[0].recorded_value(data['date']))
                    m["Reel_Production"] = float(data['pi_server'].search(reel_tag)[0].recorded_value(data['date']))
            except Exception as e:
                logging.warning(f"PI fetch failed for {machine}: {e}")

            rew = data['rewinder_df'][data['rewinder_df']['Machine'] == machine]
            m["Rewinder_Input"] = rew['TOT_MENGE'].sum() / 1000
            m["Rewinder_Output"] = rew['CH_REEL_WT'].sum() / 1000

            qc = data['qc_df'][data['qc_df']['Machine'] == machine]
            m["Qc_Rejection"] = qc[qc['REA_MOV'] == 'Repulp']['FROM_QTY'].sum() / 1000
            m["Handling_Loss"] = qc[qc['CODE'] == 'Handling Loss']['FROM_QTY'].sum() / 1000

            df_list.append(m)

        df = pd.DataFrame(df_list)
        summary = {
            "last_calculated_date": str(data['date'].date()),
            "machines": {
                m: {
                    "daily_broke": round(df[df['machine_id'] == m]['Qc_Rejection'].sum(), 2),
                    "monthly_broke": round(df[df['machine_id'] == m]['Qc_Rejection'].sum(), 2)
                } for m in df['machine_id'].unique()
            }
        }

        return df, summary

    except Exception as e:
        raise CustomException(e, sys)