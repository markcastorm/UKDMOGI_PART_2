"""
Configuration for UKDMOGI Part 2 Data Pipeline
Redemption Details of Redeemed Gilts

Centralizes all configuration settings for the pipeline:
- Project metadata and directories
- Data source configuration
- Column mappings
- Metadata defaults
- Web scraping selectors
- Output file naming

Based on CHEF_NOVARTIS architecture
"""

import os
from datetime import datetime
from pathlib import Path

# =============================================================================
# PROJECT METADATA
# =============================================================================

PROJECT_NAME = "UKDMOGI_DATA_PART_2"
PROVIDER = "AfricaAI"
SOURCE = "UKDMO"
SOURCE_DESCRIPTION = "United Kingdom Debt Management Office"
COUNTRY = "GBR"  # United Kingdom
CURRENCY = "GBP"  # British Pound Sterling
DATASET = "UKDMOGI"

# =============================================================================
# TIMESTAMPED DIRECTORY STRUCTURE
# =============================================================================

# Generate timestamp for this run (YYYYMMDD_HHMMSS format)
RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Date stamp for file names (YYYYMMDD format)
DATE_STAMP = datetime.now().strftime("%Y%m%d")

# Base directory (where this config.py file is located)
BASE_DIR = Path(__file__).parent

# Timestamped subdirectories for this run
DOWNLOADS_DIR = BASE_DIR / "downloads" / RUN_TIMESTAMP
OUTPUT_DIR = BASE_DIR / "output" / RUN_TIMESTAMP
LOGS_DIR = BASE_DIR / "logs" / RUN_TIMESTAMP

# "Latest" directories (always point to most recent run)
LATEST_DOWNLOADS_DIR = BASE_DIR / "downloads" / "latest"
LATEST_OUTPUT_DIR = BASE_DIR / "output" / "latest"
LATEST_LOGS_DIR = BASE_DIR / "logs" / "latest"

# Log file path
LOG_FILEPATH = LOGS_DIR / f"ukdmogi_part2_{RUN_TIMESTAMP}.log"

# =============================================================================
# PART 2: REDEMPTION DETAILS OF REDEEMED GILTS
# =============================================================================

# Part 2 Data Source
PART2_URL = "https://www.dmo.gov.uk/data/ExportReport?reportCode=D1C"
PART2_REPORT_CODE = "D1C"
PART2_REPORT_NAME = "Redemption Details of Redeemed Gilts"

# Part 2 Output Configuration
OUTPUT_CODE_MNEMONIC = "UKDMOGI.GILTREDEMP.B"
OUTPUT_BASE_CODE = "UKDMOGI.GILTREDEMP"
OUTPUT_DESCRIPTION = "Gilt Redemptions"
OUTPUT_FREQUENCY = "B"  # Business day

# Part 2 Column Names in Downloaded Excel File
EXCEL_REDEMPTION_DATE_COLUMN = "Redemption Date"
EXCEL_NOMINAL_AMOUNT_COLUMN = "Nominal amount outstanding at redemption"  # Will match with "£ million" suffix

# =============================================================================
# DATA PROCESSING CONFIGURATION
# =============================================================================

# Year filtering configuration
# Set to None for default (2024 onwards), or specify a year like 2023, 2022, etc.
START_YEAR = None  # None = default to 2024, or set specific year like 2023
DEFAULT_START_YEAR = 2024  # Default minimum year when START_YEAR is None

# Current year (for reference)
CURRENT_YEAR = datetime.now().year

# Value transformation
NEGATE_VALUES = True  # Redemptions should be negative (reduce outstanding debt)

# Weekend consolidation
CONSOLIDATE_WEEKENDS = True  # Move weekend dates to Monday
AGGREGATE_DUPLICATES = True  # Sum values for duplicate dates

# Date format
DATE_FORMAT_INPUT = "%Y-%m-%d"  # Input date format from Excel
DATE_FORMAT_OUTPUT = "%Y-%m-%d"  # Output date format (YYYY-MM-DD)

# Decimal places for values
DECIMAL_PLACES = 4

# Blank value replacement
BLANK_VALUE_REPLACEMENT = ""

# =============================================================================
# OUTPUT FILE NAMING
# =============================================================================

# Output file name patterns (Excel format)
DATA_FILENAME_PART2 = f"UKDMOGI_DATA_PART_2_{DATE_STAMP}.xlsx"
META_FILENAME_PART2 = f"UKDMOGI_META_PART_2_{DATE_STAMP}.xlsx"

# =============================================================================
# METADATA CONFIGURATION
# =============================================================================

# Metadata column headers
METADATA_COLUMNS = [
    "CODE_MNEMONIC",
    "DESCRIPTION",
    "FREQUENCY",
    "MULTIPLIER",
    "AGGREGATION_TYPE",
    "UNIT_TYPE",
    "DATA_TYPE",
    "DATA_UNIT",
    "SEASONALLY_ADJUSTED",
    "ANNUALIZED",
    "PROVIDER_MEASURE_URL",
    "PROVIDER",
    "SOURCE",
    "SOURCE_DESCRIPTION",
    "COUNTRY",
    "DATASET"
]

# Part 2 Metadata
METADATA_PART2 = {
    "CODE_MNEMONIC": OUTPUT_BASE_CODE,
    "DESCRIPTION": OUTPUT_DESCRIPTION,
    "FREQUENCY": OUTPUT_FREQUENCY,
    "MULTIPLIER": "6",
    "AGGREGATION_TYPE": "SUM",  # Sum values for duplicate dates
    "UNIT_TYPE": "FLOW",  # Flow data (change in stock)
    "DATA_TYPE": "CURRENCY",
    "DATA_UNIT": CURRENCY,
    "SEASONALLY_ADJUSTED": "NSA",
    "ANNUALIZED": "FALSE",
    "PROVIDER_MEASURE_URL": PART2_URL,
    "PROVIDER": PROVIDER,
    "SOURCE": SOURCE,
    "SOURCE_DESCRIPTION": SOURCE_DESCRIPTION,
    "COUNTRY": COUNTRY,
    "DATASET": DATASET
}

# =============================================================================
# WEB SCRAPING CONFIGURATION
# =============================================================================

# Cookie Consent Banner
COOKIE_CONSENT_BUTTON_ID = "ccc-recommended-settings"
COOKIE_WAIT_TIMEOUT = 10  # seconds

# Excel Download Button (Part 2)
EXCEL_BUTTON_XPATH = "//button[contains(text(), 'Excel')]"
EXCEL_BUTTON_ONCLICK = "GenerateDownloadDataReport('xls')"

# Browser Configuration
HEADLESS_MODE = False  # Set to True for background operation (no browser window)
ELEMENT_WAIT_TIMEOUT = 20  # seconds
DOWNLOAD_WAIT_TIMEOUT = 60  # seconds

# Download Validation
MIN_FILE_SIZE = 1024  # minimum file size in bytes (1 KB)

# =============================================================================
# DATA VALIDATION CONFIGURATION
# =============================================================================

# Minimum number of data rows required for valid output
MIN_DATA_ROWS = 1

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Log levels
CONSOLE_LOG_LEVEL = "INFO"  # Console output level
FILE_LOG_LEVEL = "DEBUG"    # File output level (more detailed)

# Debug mode (enables additional logging)
DEBUG_MODE = True


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_directories():
    """
    Create all necessary directories for the pipeline run
    """
    directories = [
        DOWNLOADS_DIR,
        OUTPUT_DIR,
        LOGS_DIR,
        LATEST_DOWNLOADS_DIR,
        LATEST_OUTPUT_DIR,
        LATEST_LOGS_DIR
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def print_config_summary():
    """
    Print a summary of current configuration
    """
    print("\n" + "="*70)
    print(f"CONFIGURATION SUMMARY - {PROJECT_NAME}")
    print("="*70)
    print(f"Provider:          {PROVIDER}")
    print(f"Source:            {SOURCE_DESCRIPTION}")
    print(f"Country:           {COUNTRY}")
    print(f"Currency:          {CURRENCY}")
    print(f"")
    print(f"Part 2 URL:        {PART2_URL}")
    print(f"Report Code:       {PART2_REPORT_CODE}")
    print(f"Report Name:       {PART2_REPORT_NAME}")
    print(f"")
    print(f"Output Code:       {OUTPUT_CODE_MNEMONIC}")
    print(f"Description:       {OUTPUT_DESCRIPTION}")
    print(f"Frequency:         {OUTPUT_FREQUENCY}")
    print(f"")
    print(f"Start Year:        {START_YEAR if START_YEAR else f'{DEFAULT_START_YEAR} (default)'}")
    print(f"Current Year:      {CURRENT_YEAR}")
    print(f"Negate Values:     {NEGATE_VALUES}")
    print(f"Consolidate Weekends: {CONSOLIDATE_WEEKENDS}")
    print(f"Aggregate Duplicates: {AGGREGATE_DUPLICATES}")
    print(f"")
    print(f"Run Timestamp:     {RUN_TIMESTAMP}")
    print(f"Downloads Dir:     {DOWNLOADS_DIR}")
    print(f"Output Dir:        {OUTPUT_DIR}")
    print(f"Logs Dir:          {LOGS_DIR}")
    print(f"")
    print(f"Headless Mode:     {HEADLESS_MODE}")
    print(f"Debug Mode:        {DEBUG_MODE}")
    print("="*70 + "\n")


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("\nTesting config.py module...")
    print_config_summary()

    print("\nCreating directories...")
    create_directories()
    print("[OK] All directories created successfully")

    print("\nMetadata columns:")
    for col in METADATA_COLUMNS:
        print(f"  - {col}")

    print("\nPart 2 Metadata:")
    for key, value in METADATA_PART2.items():
        print(f"  {key}: {value}")

    print("\n[OK] config.py module test completed successfully")
