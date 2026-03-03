"""
File Generator for UKDMOGI Part 2 Pipeline
Generates DATA and META Excel files in required format

Handles:
- Weekend consolidation (move Saturday/Sunday to Monday)
- Duplicate date aggregation (SUM values for same day)
- DATA Excel generation with exact header format
- META Excel generation with all metadata fields
- File copying to 'latest' folder
- Timestamped file naming

Based on CHEF_NOVARTIS architecture
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

import config
from logger_setup import setup_logger

# Initialize logger
logger = setup_logger(__name__)


class UKDMOFileGenerator:
    """
    File generator for UKDMOGI Part 2 output files

    Creates DATA and META Excel files with weekend consolidation
    and duplicate date aggregation.
    """

    def __init__(self):
        """Initialize file generator with output directories"""
        self.output_dir = str(config.OUTPUT_DIR.absolute())
        self.latest_dir = str(config.LATEST_OUTPUT_DIR.absolute())

        # Ensure directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.latest_dir, exist_ok=True)

        logger.info("UKDMOFileGenerator initialized")
        logger.debug(f"Output directory: {self.output_dir}")
        logger.debug(f"Latest directory: {self.latest_dir}")

    def move_weekend_to_monday(self, date_str):
        """
        Move weekend dates to the following Monday

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            str: Adjusted date (Monday if weekend, otherwise unchanged)
        """
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')

            # Check if weekend (Saturday=5, Sunday=6)
            if date_obj.weekday() == 5:  # Saturday
                # Move to Monday (+2 days)
                date_obj = date_obj + timedelta(days=2)
                logger.debug(f"Moved Saturday {date_str} to Monday {date_obj.strftime('%Y-%m-%d')}")
                return date_obj.strftime('%Y-%m-%d')

            elif date_obj.weekday() == 6:  # Sunday
                # Move to Monday (+1 day)
                date_obj = date_obj + timedelta(days=1)
                logger.debug(f"Moved Sunday {date_str} to Monday {date_obj.strftime('%Y-%m-%d')}")
                return date_obj.strftime('%Y-%m-%d')

            # Weekday - no change
            return date_str

        except Exception as e:
            logger.warning(f"Error adjusting date {date_str}: {e}")
            return date_str

    def aggregate_duplicate_dates(self, parsed_data):
        """
        Aggregate values for duplicate dates (SUM)

        Args:
            parsed_data: List of {"date": str, "nominal_amount": float/None}

        Returns:
            list: Aggregated data with unique dates
        """
        if not parsed_data:
            return parsed_data

        logger.info("Aggregating duplicate dates...")

        # Dictionary to track date -> total amount
        date_totals = {}

        for row in parsed_data:
            date_str = row['date']
            amount = row['nominal_amount']

            if amount is None:
                continue  # Skip None values

            if date_str in date_totals:
                # Add to existing total
                date_totals[date_str] += amount
            else:
                # First occurrence
                date_totals[date_str] = amount

        # Convert back to list format
        aggregated_data = [
            {"date": date_str, "nominal_amount": total}
            for date_str, total in sorted(date_totals.items())
        ]

        duplicate_count = len(parsed_data) - len(aggregated_data)
        if duplicate_count > 0:
            logger.info(f"Aggregated {duplicate_count} duplicate dates into {len(aggregated_data)} unique dates")
        else:
            logger.info(f"No duplicate dates found ({len(aggregated_data)} unique dates)")

        return aggregated_data

    def process_data(self, parsed_data):
        """
        Process data with weekend consolidation and aggregation

        Args:
            parsed_data: List of {"date": str, "nominal_amount": float/None}

        Returns:
            list: Processed data ready for Excel generation
        """
        logger.info("Processing data with weekend consolidation and aggregation...")

        if not parsed_data:
            return parsed_data

        # Step 1: Move weekend dates to Monday
        if config.CONSOLIDATE_WEEKENDS:
            logger.info("Consolidating weekend dates to Monday...")
            for row in parsed_data:
                row['date'] = self.move_weekend_to_monday(row['date'])

        # Step 2: Aggregate duplicate dates (after weekend consolidation)
        if config.AGGREGATE_DUPLICATES:
            parsed_data = self.aggregate_duplicate_dates(parsed_data)

        logger.info(f"[OK] Data processing complete: {len(parsed_data)} final rows")

        return parsed_data

    def create_data_file(self, parsed_data, output_path=None):
        """
        Create DATA Excel file in required format

        Format:
        Row 1: [blank], CODE_MNEMONIC
        Row 2: [blank], DESCRIPTION
        Row 3+: DATE, VALUE (negative)

        Args:
            parsed_data: List of {"date": str, "nominal_amount": float (negative)}
            output_path: Optional custom output path

        Returns:
            str: Path to created file
        """
        if output_path is None:
            output_path = os.path.join(self.output_dir, config.DATA_FILENAME_PART2)

        logger.info(f"Creating DATA file: {os.path.basename(output_path)}")

        try:
            # Prepare data for DataFrame
            data_rows = []

            # Row 1: Headers (blank, code mnemonic)
            data_rows.append(['', config.OUTPUT_CODE_MNEMONIC])

            # Row 2: Descriptions (blank, description)
            data_rows.append(['', config.OUTPUT_DESCRIPTION])

            # Row 3+: Data rows (date, value)
            for row in parsed_data:
                date_str = row['date']
                nominal_value = row['nominal_amount']

                # Format nominal value
                if nominal_value is None:
                    nominal_str = config.BLANK_VALUE_REPLACEMENT
                else:
                    # Format with appropriate decimal places
                    nominal_str = round(nominal_value, config.DECIMAL_PLACES)

                data_rows.append([date_str, nominal_str])

            # Create DataFrame and write to Excel
            df = pd.DataFrame(data_rows)

            # Write to Excel without headers or index
            df.to_excel(output_path, index=False, header=False, engine='openpyxl')

            logger.info(f"[OK] DATA file created: {len(parsed_data)} rows")
            logger.debug(f"File path: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Failed to create DATA file: {str(e)}")
            raise

    def create_meta_file(self, output_path=None):
        """
        Create META Excel file with metadata fields

        Format:
        Row 1: Column headers
        Row 2: Metadata values

        Args:
            output_path: Optional custom output path

        Returns:
            str: Path to created file
        """
        if output_path is None:
            output_path = os.path.join(self.output_dir, config.META_FILENAME_PART2)

        logger.info(f"Creating META file: {os.path.basename(output_path)}")

        try:
            # Prepare data
            meta_rows = []

            # Row 1: Column headers
            # Add empty first column to match reference format
            headers = [''] + config.METADATA_COLUMNS
            meta_rows.append(headers)

            # Row 2: Metadata values
            meta = config.METADATA_PART2
            values = [config.OUTPUT_CODE_MNEMONIC]  # First column is the full code

            # Add metadata values in order
            for col in config.METADATA_COLUMNS:
                values.append(meta.get(col, ''))

            meta_rows.append(values)

            # Create DataFrame and write to Excel
            df = pd.DataFrame(meta_rows)

            # Write to Excel without headers or index
            df.to_excel(output_path, index=False, header=False, engine='openpyxl')

            logger.info(f"[OK] META file created")
            logger.debug(f"File path: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Failed to create META file: {str(e)}")
            raise

    def copy_to_latest(self, file_path):
        """
        Copy file to 'latest' directory

        Args:
            file_path: Path to file to copy

        Returns:
            str: Path to copied file in latest directory
        """
        filename = os.path.basename(file_path)
        latest_path = os.path.join(self.latest_dir, filename)

        try:
            shutil.copy2(file_path, latest_path)
            logger.debug(f"Copied to latest: {filename}")
            return latest_path

        except Exception as e:
            logger.warning(f"Failed to copy to latest: {str(e)}")
            return None

    def generate_files(self, parsed_data):
        """
        Main file generation workflow

        Args:
            parsed_data: List of {"date": str, "nominal_amount": float}

        Returns:
            dict: Result with file paths
                  {
                      "success": bool,
                      "data_file": str,
                      "meta_file": str,
                      "error": str,
                      "row_count": int
                  }
        """
        result = {
            "success": False,
            "data_file": None,
            "meta_file": None,
            "error": None,
            "row_count": 0
        }

        logger.info("Generating output files...")

        try:
            # Validate input
            if not parsed_data:
                result["error"] = "No data provided for file generation"
                logger.error(result["error"])
                return result

            # Process data (weekend consolidation + aggregation)
            processed_data = self.process_data(parsed_data)

            if not processed_data:
                result["error"] = "No data rows after processing"
                logger.error(result["error"])
                return result

            result["row_count"] = len(processed_data)

            # Create DATA file
            data_file = self.create_data_file(processed_data)
            result["data_file"] = data_file

            # Create META file
            meta_file = self.create_meta_file()
            result["meta_file"] = meta_file

            # Copy to latest folder
            self.copy_to_latest(data_file)
            self.copy_to_latest(meta_file)

            logger.info("[OK] All output files generated successfully")

            # Summary
            logger.info("\nGenerated files:")
            logger.info(f"  DATA: {os.path.basename(data_file)}")
            logger.info(f"  META: {os.path.basename(meta_file)}")
            logger.info(f"\nFiles saved to:")
            logger.info(f"  Timestamped: {self.output_dir}")
            logger.info(f"  Latest:      {self.latest_dir}")

            result["success"] = True
            return result

        except Exception as e:
            logger.error(f"File generation failed: {str(e)}", exc_info=True)
            result["error"] = str(e)
            return result


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("\nTesting file_generator.py module...\n")

    # Create test data (including weekend dates and duplicates)
    test_data = [
        {"date": "2024-01-29", "nominal_amount": -1000.0},  # Monday
        {"date": "2024-01-30", "nominal_amount": -1500.0},  # Tuesday
        {"date": "2024-02-03", "nominal_amount": -2000.0},  # Saturday -> should move to Monday 2024-02-05
        {"date": "2024-02-04", "nominal_amount": -2500.0},  # Sunday -> should move to Monday 2024-02-05
        {"date": "2024-02-05", "nominal_amount": -3000.0},  # Monday -> should aggregate with moved weekend
    ]

    print("Test data (before processing):")
    for row in test_data:
        print(f"  {row['date']}: {row['nominal_amount']}")

    # Create generator and generate files
    generator = UKDMOFileGenerator()
    result = generator.generate_files(test_data)

    # Print results
    print("\n" + "="*70)
    print("FILE GENERATION RESULTS")
    print("="*70)
    print(f"Success: {result['success']}")

    if result['success']:
        print(f"Rows in output: {result['row_count']}")
        print(f"DATA file: {result['data_file']}")
        print(f"META file: {result['meta_file']}")
        print("\nExpected consolidation:")
        print("  - Saturday 2024-02-03 (-2000) + Sunday 2024-02-04 (-2500) + Monday 2024-02-05 (-3000)")
        print("  - Should result in Monday 2024-02-05: -7500")
    else:
        print(f"Error: {result['error']}")

    print("="*70)
