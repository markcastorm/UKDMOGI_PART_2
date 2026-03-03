"""
Excel Parser for UKDMOGI Part 2
Redemption Details of Redeemed Gilts

Handles:
- Smart header row detection (no hardcoded positions)
- Excel file parsing (.xls format)
- Date extraction and formatting
- Value extraction with negation (redemptions reduce debt)
- Current year filtering
- Data validation and sorting

Based on CHEF_NOVARTIS architecture
"""

import os
import pandas as pd
from datetime import datetime

import config
from logger_setup import setup_logger

# Initialize logger
logger = setup_logger(__name__)


class UKDMOParser:
    """
    Parser for UKDMOGI Part 2 Excel files

    Extracts redemption data with smart header detection,
    negates values, and filters to current year.
    """

    def __init__(self):
        """Initialize parser with column mappings from config"""
        self.date_column = config.EXCEL_REDEMPTION_DATE_COLUMN
        self.amount_column_prefix = config.EXCEL_NOMINAL_AMOUNT_COLUMN  # Will match partial string

        logger.info("UKDMOParser initialized")
        logger.debug(f"Looking for date column containing: '{self.date_column}'")
        logger.debug(f"Looking for amount column containing: '{config.EXCEL_NOMINAL_AMOUNT_COLUMN}'")

    def parse_date(self, date_value):
        """
        Parse date value to string format (YYYY-MM-DD)

        Args:
            date_value: Date value (datetime, string, or other)

        Returns:
            str: Formatted date string (YYYY-MM-DD) or None if invalid
        """
        if pd.isna(date_value):
            return None

        try:
            # If already datetime
            if isinstance(date_value, datetime):
                return date_value.strftime(config.DATE_FORMAT_OUTPUT)

            # If pandas Timestamp
            if isinstance(date_value, pd.Timestamp):
                return date_value.strftime(config.DATE_FORMAT_OUTPUT)

            # If string, try to parse
            if isinstance(date_value, str):
                # Try various date formats
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
                    try:
                        dt = datetime.strptime(date_value, fmt)
                        return dt.strftime(config.DATE_FORMAT_OUTPUT)
                    except ValueError:
                        continue

            return None

        except Exception as e:
            logger.debug(f"Error parsing date '{date_value}': {e}")
            return None

    def filter_from_start_year(self, parsed_data):
        """
        Filter data from configured start year onwards

        Uses START_YEAR from config if set, otherwise defaults to DEFAULT_START_YEAR (2024)

        Args:
            parsed_data: List of {"date": str, "nominal_amount": float/None}

        Returns:
            list: Filtered data from start year onwards
        """
        if not parsed_data:
            return parsed_data

        filtered_data = []

        # Use configured start year or default
        min_year = config.START_YEAR if config.START_YEAR is not None else config.DEFAULT_START_YEAR

        for row in parsed_data:
            try:
                year = int(row['date'][:4])  # Extract year from YYYY-MM-DD format
                if year >= min_year:
                    filtered_data.append(row)
            except (ValueError, IndexError):
                logger.debug(f"Could not extract year from date: {row['date']}")
                continue

        removed_count = len(parsed_data) - len(filtered_data)
        if removed_count > 0:
            logger.info(f"Filtered to {min_year} onwards: kept {len(filtered_data)} rows, removed {removed_count} rows from earlier years")
        else:
            logger.info(f"All {len(parsed_data)} rows are from {min_year} onwards")

        return filtered_data

    def parse_file(self, file_path):
        """
        Parse Excel file and extract redemption data

        Args:
            file_path: Path to downloaded Excel file

        Returns:
            dict: Result dictionary with parsed data
                  {
                      "success": bool,
                      "data": list of {"date": str, "nominal_amount": float (negative)},
                      "error": str,
                      "row_count": int
                  }
        """
        result = {
            "success": False,
            "data": [],
            "error": None,
            "row_count": 0
        }

        # Validate file exists
        if not os.path.exists(file_path):
            result["error"] = f"File not found: {file_path}"
            logger.error(result["error"])
            return result

        logger.info(f"Parsing Excel file: {os.path.basename(file_path)}")

        try:
            # SMART HEADER DETECTION: Find the header row automatically
            # Read first 20 rows without assuming header position
            df_preview = pd.read_excel(file_path, engine='xlrd', header=None, nrows=20)

            # Search for header row by looking for expected column names
            header_row = None
            for idx, row in df_preview.iterrows():
                row_str = ' '.join([str(cell).lower() for cell in row if pd.notna(cell)])

                # Check if this row contains our expected column names
                if 'redemption date' in row_str and 'nominal amount' in row_str:
                    header_row = idx
                    logger.info(f"Header row automatically detected at row {idx}")
                    break

            if header_row is None:
                result["error"] = "Could not find header row with expected columns (Redemption Date, Nominal amount)"
                logger.error(result["error"])
                return result

            # Now read the full file with the correct header row
            df = pd.read_excel(file_path, engine='xlrd', header=header_row)

            logger.debug(f"Excel file loaded. Shape: {df.shape}")
            logger.debug(f"Columns: {df.columns.tolist()}")

            # Find the date and nominal amount columns dynamically
            date_col_name = None
            amount_col_name = None

            for col in df.columns:
                col_str = str(col).strip()
                if self.date_column.lower() in col_str.lower():
                    date_col_name = col
                    logger.debug(f"Date column found: '{col}'")

                # Match "Nominal amount" AND "million" in column name
                if "nominal amount" in col_str.lower() and "million" in col_str.lower():
                    amount_col_name = col
                    logger.debug(f"Nominal amount column found: '{col}'")

            if not date_col_name or not amount_col_name:
                result["error"] = "Required columns not found in Excel file"
                logger.error(f"Could not find expected columns. Available: {df.columns.tolist()}")
                return result

            # Parse data rows
            parsed_data = []
            skipped_rows = 0

            for idx, row in df.iterrows():
                date_value = row[date_col_name]
                nominal_value = row[amount_col_name]

                # Parse date
                date_str = self.parse_date(date_value)

                if date_str:
                    # Apply negation if configured (redemptions reduce outstanding debt)
                    if config.NEGATE_VALUES and pd.notna(nominal_value):
                        nominal_value = -abs(nominal_value)  # Ensure negative

                    parsed_data.append({
                        "date": date_str,
                        "nominal_amount": nominal_value if pd.notna(nominal_value) else None
                    })
                else:
                    # Skip rows without valid dates
                    if idx < 10:  # Only log first few skips to avoid spam
                        logger.debug(f"Skipped row {idx}: date={date_value}, amount={nominal_value}")
                    skipped_rows += 1

            # Sort by date (ascending - oldest first)
            parsed_data.sort(key=lambda x: x["date"])

            # Log summary before filtering
            logger.info(f"Parsed {len(parsed_data)} total data rows")
            logger.debug(f"Skipped {skipped_rows} rows (no valid date)")

            if parsed_data:
                logger.debug(f"Full date range: {parsed_data[0]['date']} to {parsed_data[-1]['date']}")

            # Filter to configured start year onwards
            parsed_data = self.filter_from_start_year(parsed_data)

            min_year = config.START_YEAR if config.START_YEAR is not None else config.DEFAULT_START_YEAR

            # Validate minimum rows after filtering
            if len(parsed_data) < config.MIN_DATA_ROWS:
                result["error"] = f"Insufficient data rows from {min_year} onwards: {len(parsed_data)} (minimum: {config.MIN_DATA_ROWS})"
                logger.error(result["error"])
                return result

            # Success
            result["success"] = True
            result["data"] = parsed_data
            result["row_count"] = len(parsed_data)

            logger.info(f"[OK] Parsing completed successfully: {len(parsed_data)} rows from {min_year} onwards")

            return result

        except Exception as e:
            logger.error(f"Parsing failed: {str(e)}", exc_info=True)
            result["error"] = str(e)
            return result


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("\nTesting parser.py module...\n")

    # Test with downloaded file
    test_file = "downloads/latest/20260113 - Redemption Details of Redeemed Gilts.xls"

    if not os.path.exists(test_file):
        print(f"[ERROR] Test file not found: {test_file}")
        print("Please run scraper.py first to download the file")
        exit(1)

    # Create parser and parse
    parser = UKDMOParser()
    result = parser.parse_file(test_file)

    # Print results
    print("\n" + "="*70)
    print("PARSING RESULTS")
    print("="*70)
    print(f"Success: {result['success']}")

    if result['success']:
        min_year = config.START_YEAR if config.START_YEAR is not None else config.DEFAULT_START_YEAR
        print(f"Rows parsed (from {min_year} onwards): {result['row_count']}")
        print(f"\nFirst 5 rows:")
        for i, row in enumerate(result['data'][:5]):
            print(f"  {i+1}. {row['date']}: {row['nominal_amount']}")
        print(f"\nLast 5 rows:")
        for i, row in enumerate(result['data'][-5:]):
            print(f"  {len(result['data'])-4+i}. {row['date']}: {row['nominal_amount']}")
    else:
        print(f"Error: {result['error']}")

    print("="*70)
