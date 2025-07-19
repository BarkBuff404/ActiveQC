import pandas as pd
from datetime import datetime, timedelta
from src.utils.db import get_db_connection
from src.utils.logger import logging
from src.utils.exception import CustomException
from src.config.settings import settings
from PIconnect.PI import PIServer # type: ignore
import sys

def fetch_all_data():
    """
        Fetch all relevant data from the database and PI server.
        Returns: dict: Contains DataFrames for SAP, Rewinder, QC data and PI server connection.
        Raises: CustomException: If any error occurs during data fetching.
    """
    try:
        conn = get_db_connection()
        calculation_date_dt = datetime.now() - timedelta(days=1)
        date_db = calculation_date_dt.strftime("%Y%m%d")
        date_qc = calculation_date_dt.strftime("%d.%m.%Y")

        # SAP data
        query_sap = f"""
        SELECT * FROM MB51_MATDOC 
        WHERE werks = 5000 
        AND BUDAT LIKE {date_db} 
        AND BWART BETWEEN 101 AND 102 
        AND LGORT LIKE 'PM%'"""
        sap_df = pd.read_sql(query_sap, conn)
        sap_df = sap_df.drop_duplicates(subset='CHARG')
        sap_df['machine'] = sap_df['LGORT'].map(settings.MACHINE_MAP_SAP)

        # Rewinder data
        query_rew = f"SELECT * FROM ZPR020_REWLOG WHERE BUDAT = '{date_db}'"
        rewinder_df = pd.read_sql(query_rew, conn)
        rewinder_df = rewinder_df.drop_duplicates(subset='OP_CHARG')
        rewinder_df['Machine'] = rewinder_df['BATCH'].apply(lambda x: settings.MACHINE_MAP_REWINDER.get(x[4:6], 'Unknown'))

        # QC data
        query_qc = f"SELECT * FROM ZQM008_REJ WHERE werks = 5000 AND CDATE = '{date_qc}'"
        qc_df = pd.read_sql(query_qc, conn)
        qc_df['Machine'] = qc_df['LGORT'].map(settings.MACHINE_MAP_QC)

        conn.close()

        # PI server
        try:
            pi_server = PIServer(settings.PI_SERVER_ADDRESS)
        except Exception as e:
            logging.warning("PI Server unavailable.")
            pi_server = None

        return {
            "sap_df": sap_df,
            "rewinder_df": rewinder_df,
            "qc_df": qc_df,
            "pi_server": pi_server,
            "date": calculation_date_dt
        }

    except Exception as e:
        raise CustomException(e, sys)