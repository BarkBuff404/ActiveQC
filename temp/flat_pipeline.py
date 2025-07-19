# -*- coding: utf-8 -*-
"""
Created on XXX XXX XX XX:XX:XX XXXX
@author: XXXXXX
"""

import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine # type: ignore
from PIconnect.PI import PIServer # type: ignore
from dotenv import load_dotenv # type: ignore
import json
import os
import logging
import time

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection details
load_dotenv()
DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING")
PI_SERVER_ADDRESS = os.getenv("PI_SERVER_ADDRESS")

# Output data files
DAILY_HISTORY_FILE = 'data/daily_metrics_history.feather'
DASHBOARD_SUMMARY_FILE = 'data/dashboard_summary.json'
 
# Mapping for machine codes (from your Streamlit app)
MACHINE_MAP_SAP = {'PM1': 'PM1', 'PM3': 'PM3', 'PM4': 'PM4'}
MACHINE_MAP_REWINDER = {'01': 'PM1', '03': 'PM3', '04': 'PM4'}
MACHINE_MAP_QC = {'RP1': 'PM1', 'RP3': 'PM3', 'RP4': 'PM4', 'C502': 'PM3'} # Adjust 'C502' if not PM3
Broke_columns={'FH3','FH4','FH1'}
 
# PI Tags for QCS & Reel Production
PI_TAGS = {
    'PM1': ('PSPD_TBN_PM01_QCS:DayTonnage', 'PSPD_TBN_PM01_QCS:ReelTonnage'),
    'PM3': ('PSPD_TBN_PM03_QCS:DayTonnage', 'PSPD_TBN_PM03_QCS:ReelTonnage'),
    'PM4': ('PSPD_TBN_PM04_QCS:DayTonnage', 'PSPD_TBN_PM04_QCS:ReelTonnage'),
}
 
# --- Ensure Directories Exist ---
os.makedirs('data', exist_ok=True)
 
# --- DB Connection Helper ---
def get_db_connection():
    try:
        engine = create_engine(DB_CONNECTION_STRING)
        return engine.connect()
    except Exception as e:
        logging.error(f"DB Connection failed: {e}")
        return None
 
# --- Main Processing Logic ---
def run_daily_processing():
    calculation_date_dt = datetime.now() - timedelta(days=1)
    calculation_date_str_db = calculation_date_dt.strftime("%Y%m%d")
    calculation_date_str_pi = datetime.now().replace(hour=6,minute=0,second=0,microsecond=0)
    print(calculation_date_str_pi)
    calculation_date_str_qc_db = calculation_date_dt.strftime("%d.%m.%Y")
 
    logging.info(f"Starting daily data processing for: {calculation_date_dt.isoformat().split('T')[0]}")
 
    conn = get_db_connection()
    if not conn:
        logging.error("Database connection not available. Aborting daily processing.")
        return
 
    daily_calculated_metrics = []
 
    all_machines = sorted(list(PI_TAGS.keys()))
    if not all_machines:
        logging.error("No machines defined in PI_TAGS. Cannot proceed.")
        conn.close()
        return
 
    # --- Fetch SAP Production (Step 1) ---
    logging.info("Fetching SAP Production data...")
    sap_df = pd.DataFrame()
    try:
        query_sap = f"""select  * from MB51_MATDOC where werks = 5000 AND BUDAT LIKE {calculation_date_str_db} and BWART BETWEEN 101 AND 102 AND LGORT LIKE 'PM%'"""
        sap_df = pd.read_sql(query_sap, conn)
        sap_df = sap_df.drop_duplicates(subset='CHARG')
        #sap_df = sap_df[sap_df['GMNGA'] != 0].drop(columns=['MANDT', 'RTCODE', 'PROD', 'ERDAT', 'ERNAM', 'UZEIT', 'TIMESTAMP1', 'FLAG'], errors='ignore')
        #sap_df = sap_df.drop_duplicates()
        print(sap_df['MENGE'].sum())
        sap_df['machine'] = sap_df['LGORT'].map(MACHINE_MAP_SAP)
        #sap_df['machine'] = sap_df['ARBPL'].map(MACHINE_MAP_SAP)
        print(sap_df['MENGE'].sum())
        logging.info(f"Fetched {len(sap_df)} rows from SAP.")
    except Exception as e:
        logging.error(f"Error fetching SAP Production: {e}")
 
    # --- Fetch Rewinder Data (Step 3) ---
    logging.info("Fetching Rewinder data...")
    rewinder_df = pd.DataFrame()
    try:
        query_rew = f"SELECT * FROM ZPR020_REWLOG WHERE BUDAT = '{calculation_date_str_db}'"
        rewinder_df = pd.read_sql(query_rew, conn)
        rewinder_df = rewinder_df.drop_duplicates(subset=['OP_CHARG'], ignore_index=True)
        rewinder_df = rewinder_df.dropna(subset=['BATCH'])
        rewinder_df['Machine'] = rewinder_df['BATCH'].apply(lambda x: MACHINE_MAP_REWINDER.get(x[4:6], 'Unknown'))
        logging.info(f"Fetched {len(rewinder_df)} rows from Rewinder.")
    except Exception as e:
        logging.error(f"Error fetching Rewinder Data: {e}")
 
    # --- Fetch QC & Handling Loss (Step 4) ---
    logging.info("Fetching QC & Handling Loss data...")
    qc_df = pd.DataFrame()
    try:
        query_qc = f""" SELECT * FROM ZQM008_REJ WHERE werks = 5000 AND CDATE = '{calculation_date_str_qc_db}' """
        qc_df = pd.read_sql(query_qc, conn)
        qc_df = qc_df.drop_duplicates(subset='BATCH', ignore_index=True)
        qc_df['Machine'] = qc_df['LGORT'].map(MACHINE_MAP_QC)
        logging.info(f"Fetched {len(qc_df)} rows from QC.")
    except Exception as e:
        logging.error(f"Error fetching QC & Handling Loss: {e}")

    conn.close() # Close DB connection after fetching all data
 
    # --- Process data for each machine ---
    pi_server_connected = False
    pi_server = None
    try:
        pi_server = PIServer(PI_SERVER_ADDRESS)
        pi_server_connected = True
        logging.info("Connected to PI Server.")
    except Exception as e:
        logging.error(f"Failed to connect to PI Server: {e}. QCS/Reel data will be zero for all machines.")
 
    for machine_id in all_machines:
        metrics_for_machine = {
'calculation_date': calculation_date_dt.date(),
            'machine_id': machine_id,
            'SAP_Production': 0.0,
            'QCS_Production': 0.0,
            'Reel_Production': 0.0,
            'Actual_QCS_Production': 0.0,
            'Jumbo_Cutoff': 0.0,
            'Rewinder_Input': 0.0,
            'Rewinder_Output': 0.0,
            'Rewinder_Loss': 0.0,
            'Qc_Rejection': 0.0,
            'Handling_Loss': 0.0,
            'Total_Loss': 0.0,
            'Shrinkage_Percent': 0.0,
            'Actual_Loss': 0.0,
            'Actual_Shrinkage_Percent': 0.0
        }
 
        # SAP Production
        machine_sap_tons = sap_df[sap_df['machine'] == machine_id]['MENGE'].sum()/1000
        metrics_for_machine['SAP_Production'] = round(machine_sap_tons, 2)
        print(machine_sap_tons)

        # QCS and Reel Production (Step 2)
        if pi_server_connected:
            qcs_tag, reel_tag = PI_TAGS.get(machine_id, (None, None))
            if qcs_tag and reel_tag:
                current_qcs_val = 0.0 # Initialize to 0 for this specific machine's PI data
                current_reel_val = 0.0 # Initialize to 0 for this specific machine's PI data
                
                try:
                    # Search for the QCS tag
                    qcs_point_list = pi_server.search(qcs_tag)
                    if not qcs_point_list: # If list is empty, tag not found/accessible
                        logging.warning(f"PI tag '{qcs_tag}' not found or accessible for {machine_id}. QCS data will be 0.")
                    else:
                        current_qcs_val = qcs_point_list[0].recorded_value(calculation_date_str_pi).iloc[0]
                    
                    # Search for the Reel tag
                    reel_point_list = pi_server.search(reel_tag)
                    if not reel_point_list: # If list is empty, tag not found/accessible
                        logging.warning(f"PI tag '{reel_tag}' not found or accessible for {machine_id}. Reel data will be 0.")
                    else:
                        current_reel_val = reel_point_list[0].recorded_value(calculation_date_str_pi).iloc[0]
 
                    actual_qcs = current_qcs_val - current_reel_val
                    jumbo_cutoff = actual_qcs - metrics_for_machine['SAP_Production']
 
                    metrics_for_machine.update({
                        'QCS_Production': round(current_qcs_val, 2),
                        'Reel_Production': round(current_reel_val, 2),
                        'Actual_QCS_Production': round(actual_qcs, 2),
                        'Jumbo_Cutoff': round(jumbo_cutoff, 2)
                    })
                except Exception as e:
                    # This catch handles errors during recorded_value, or other PI related issues
                    logging.warning(f"General PI data fetch error for {machine_id} on {calculation_date_dt.date()}: {e}. Setting QCS/Reel data to 0.")
                    # Values remain 0.0 from initialization of current_qcs_val/current_reel_val and metrics_for_machine
            else:
                logging.warning(f"PI tags not defined for {machine_id} in PI_TAGS configuration. Skipping QCS/Reel for this machine and setting to 0.")
        else:
            logging.warning(f"PI Server not connected. QCS/Reel data for {machine_id} will be 0.")
 
 
        # Rewinder Data (Step 3)
        machine_rew_df = rewinder_df[rewinder_df['Machine'] == machine_id]
        if not machine_rew_df.empty:
            rew_in = machine_rew_df['TOT_MENGE'].sum() / 1000
            rew_out = machine_rew_df['CH_REEL_WT'].sum() / 1000
            rew_loss = rew_in - rew_out
            metrics_for_machine.update({
                'Rewinder_Input': round(rew_in, 2),
                'Rewinder_Output': round(rew_out, 2),
                'Rewinder_Loss': round(rew_loss, 2)
            })
        else:
            logging.info(f"No rewinder data for {machine_id} on {calculation_date_dt.date()}.")
 
 
        # QC & Handling Loss (Step 4)
        machine_qc_df = qc_df[qc_df['Machine'] == machine_id]
        qc_rej = machine_qc_df[(machine_qc_df['REA_MOV'] == 'Repulp')]['FROM_QTY'].sum() / 1000
        handling_loss = machine_qc_df[
            (~machine_qc_df['LGORT'].isin(['FH1', 'FH3', 'FH4'])) &
            (machine_qc_df['CODE'] == 'Handling Loss')
        ]['FROM_QTY'].sum() / 1000
        metrics_for_machine.update({
            'Qc_Rejection': round(qc_rej, 2),
            'Handling_Loss': round(handling_loss, 2)
        })
 
 
        # Final Calculations (Step 5)
        rew_loss = metrics_for_machine['Rewinder_Loss']
        qc_rej = metrics_for_machine['Qc_Rejection']
        handling = metrics_for_machine['Handling_Loss']
        rew_in = metrics_for_machine['Rewinder_Input']
        jumbo = metrics_for_machine['Jumbo_Cutoff']
 
        total_loss = rew_loss + qc_rej + handling
        shrinkage = round((total_loss / rew_in) * 100, 2) if rew_in else 0
 
        actual_loss = jumbo + total_loss
        actual_shrinkage = round((actual_loss / rew_in) * 100, 2) if rew_in else 0
 
        metrics_for_machine.update({
            'Total_Loss': round(total_loss, 2),
            'Shrinkage_Percent': shrinkage,
            'Actual_Loss': round(actual_loss, 2),
            'Actual_Shrinkage_Percent': actual_shrinkage
        })
 
        daily_calculated_metrics.append(metrics_for_machine)
    
    # --- Update Historical Data File ---
    new_daily_df = pd.DataFrame(daily_calculated_metrics)
    if not new_daily_df.empty:
        new_daily_df['calculation_date'] = pd.to_datetime(new_daily_df['calculation_date']).dt.date
    
    if os.path.exists(DAILY_HISTORY_FILE):
        historical_df = pd.read_feather(DAILY_HISTORY_FILE)
        historical_df['calculation_date'] = pd.to_datetime(historical_df['calculation_date']).dt.date
        historical_df = historical_df[
~((historical_df['calculation_date'] == calculation_date_dt.date()) &
              (historical_df['machine_id'].isin(new_daily_df['machine_id'])))
        ]
        historical_df = pd.concat([historical_df, new_daily_df], ignore_index=True)
    else:
        historical_df = new_daily_df
 
    historical_df = historical_df.sort_values(by=['calculation_date', 'machine_id']).reset_index(drop=True)
    historical_df.to_feather(DAILY_HISTORY_FILE)
    logging.info(f"Historical data updated in {DAILY_HISTORY_FILE}")




 # --- Update Dashboard Summary File ---
    summary_for_json = {
        "last_calculated_date": calculation_date_dt.isoformat().split('T')[0],
        "machines": {}
    }
 
    current_month_start = datetime(calculation_date_dt.year, calculation_date_dt.month, 1).date()
 
    for machine_id in all_machines:
        machine_hist_df = historical_df[historical_df['machine_id'] == machine_id]
 
        day_broke = machine_hist_df[machine_hist_df['calculation_date'] == calculation_date_dt.date()]['Total_Loss'].sum()
 
        month_broke = machine_hist_df[
            (machine_hist_df['calculation_date'] >= current_month_start) &
            (machine_hist_df['calculation_date'] <= calculation_date_dt.date())
        ]['Total_Loss'].sum()
 
        summary_for_json["machines"][machine_id] = {
            "daily_broke": round(day_broke, 2),
            "monthly_broke": round(month_broke, 2)
        }
 
    with open(DASHBOARD_SUMMARY_FILE, 'w') as f:
        json.dump(summary_for_json, f, indent=4)
    logging.info(f"Dashboard summary updated in {DASHBOARD_SUMMARY_FILE}")
 
    logging.info("Daily processing completed successfully.")
    
file = open(r"C:\Users\126215\Desktop\Broke dashboard\task.txt",'a')
file.write(f'{datetime.now()} - the script ran \n')
 
if __name__ == '__main__':
    while True:
        print("Running data processing:")
        try:
            run_daily_processing()
        except Exception as e:
            print(f"Processing failed:{e}")
        print("sleeping for 10 mins")
        time.sleep(600)
 