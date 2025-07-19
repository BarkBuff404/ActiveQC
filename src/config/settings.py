# -*- coding: utf-8 -*-
"""
Configuration settings for ActiveQC application.
Centralized configuration management for database connections, file paths, and mappings.
"""

import os
from dotenv import load_dotenv # type: ignore

load_dotenv()

class Settings:
    DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING", "")
    PI_SERVER_ADDRESS = os.getenv("PI_SERVER_ADDRESS", "")

    HISTORY_FILE = "data/daily_metrics_history.feather"
    SUMMARY_FILE = "data/dashboard_summary.json"
    LOG_DIR = "tests/logs"

    MACHINE_MAP_SAP = {'PM1': 'PM1', 'PM3': 'PM3', 'PM4': 'PM4'}
    MACHINE_MAP_REWINDER = {'01': 'PM1', '03': 'PM3', '04': 'PM4'}
    MACHINE_MAP_QC = {'RP1': 'PM1', 'RP3': 'PM3', 'RP4': 'PM4', 'C502': 'PM3'}

    PI_TAGS = {
        'PM1': ('PSPD_TBN_PM01_QCS:DayTonnage', 'PSPD_TBN_PM01_QCS:ReelTonnage'),
        'PM3': ('PSPD_TBN_PM03_QCS:DayTonnage', 'PSPD_TBN_PM03_QCS:ReelTonnage'),
        'PM4': ('PSPD_TBN_PM04_QCS:DayTonnage', 'PSPD_TBN_PM04_QCS:ReelTonnage'),
    }

settings = Settings()