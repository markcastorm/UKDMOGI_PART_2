"""
Orchestrator for UKDMOGI Part 2 Data Pipeline
Redemption Details of Redeemed Gilts

Main workflow coordinator that manages:
1. Web scraping (download Excel file)
2. Data parsing (extract and transform)
3. File generation (create DATA and META files)

Based on CHEF_NOVARTIS architecture
"""

import sys
import signal
from datetime import datetime

import config
from logger_setup import setup_logger, log_section_header, log_step
from scraper import UKDMOScraper
from parser import UKDMOParser
from file_generator import UKDMOFileGenerator

# Initialize logger
logger = setup_logger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle CTRL+C gracefully"""
    global shutdown_requested
    print("\n\n[WARNING] Shutdown requested by user (CTRL+C)")
    print("Cleaning up...")
    shutdown_requested = True
    sys.exit(130)  # Exit code for CTRL+C


# Register signal handler
signal.signal(signal.SIGINT, signal_handler)


def print_banner():
    """Print application banner"""
    banner = """
    ==================================================================

              UK DEBT MANAGEMENT OFFICE DATA SCRAPER
                    Gilt Redemption Data Pipeline

                         Part 2: Redemption Details
                       of Redeemed Gilts

    ==================================================================
    """
    print(banner)


def print_configuration():
    """Print current configuration summary"""
    config_text = f"""
    Configuration:
    -----------------------------------------------------------------
    Project:           {config.PROJECT_NAME}
    Provider:          {config.PROVIDER}
    Source:            {config.SOURCE_DESCRIPTION}

    Target URL:        {config.PART2_URL}
    Report:            {config.PART2_REPORT_NAME}

    Start Year:        {config.START_YEAR if config.START_YEAR else f'{config.DEFAULT_START_YEAR} (default)'}
    Negate Values:     {config.NEGATE_VALUES}
    Weekend Consolidation: {config.CONSOLIDATE_WEEKENDS}
    Aggregate Duplicates:  {config.AGGREGATE_DUPLICATES}

    Run Timestamp:     {config.RUN_TIMESTAMP}
    Output Directory:  {config.OUTPUT_DIR}
    Downloads:         {config.DOWNLOADS_DIR}
    Logs:              {config.LOG_FILEPATH}

    Headless Mode:     {config.HEADLESS_MODE}
    Debug Mode:        {config.DEBUG_MODE}
    -----------------------------------------------------------------
    """
    print(config_text)


def setup_environment():
    """
    Setup environment and create necessary directories

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        log_section_header(logger, "ENVIRONMENT SETUP")

        logger.info("Creating directory structure...")
        config.create_directories()
        logger.info("[OK] All directories created")

        return True

    except Exception as e:
        logger.error(f"Environment setup failed: {str(e)}", exc_info=True)
        return False


def run_scraper():
    """
    Run web scraping stage

    Returns:
        dict: Scraper result with file path
    """
    log_section_header(logger, "STAGE 1: WEB SCRAPING")

    try:
        scraper = UKDMOScraper()
        result = scraper.scrape_part2()

        if result['success']:
            logger.info(f"\n[OK] Scraping completed successfully")
            logger.info(f"Downloaded file: {result['file_path']}")
        else:
            logger.error(f"\n[ERROR] Scraping failed: {result['error']}")

        return result

    except Exception as e:
        logger.error(f"Scraper stage failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "file_path": None,
            "error": str(e)
        }


def run_parser(file_path):
    """
    Run data parsing stage

    Args:
        file_path: Path to downloaded Excel file

    Returns:
        dict: Parser result with extracted data
    """
    log_section_header(logger, "STAGE 2: DATA PARSING")

    try:
        parser = UKDMOParser()
        result = parser.parse_file(file_path)

        if result['success']:
            logger.info(f"\n[OK] Parsing completed successfully")
            logger.info(f"Rows extracted (year {config.CURRENT_YEAR}): {result['row_count']}")
        else:
            logger.error(f"\n[ERROR] Parsing failed: {result['error']}")

        return result

    except Exception as e:
        logger.error(f"Parser stage failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "data": [],
            "error": str(e),
            "row_count": 0
        }


def run_generator(parsed_data):
    """
    Run file generation stage

    Args:
        parsed_data: List of parsed data dictionaries

    Returns:
        dict: Generator result with file paths
    """
    log_section_header(logger, "STAGE 3: FILE GENERATION")

    try:
        generator = UKDMOFileGenerator()
        result = generator.generate_files(parsed_data)

        if result['success']:
            logger.info(f"\n[OK] File generation completed successfully")
            logger.info(f"Final rows (after consolidation): {result['row_count']}")
        else:
            logger.error(f"\n[ERROR] File generation failed: {result['error']}")

        return result

    except Exception as e:
        logger.error(f"Generator stage failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "data_file": None,
            "meta_file": None,
            "error": str(e),
            "row_count": 0
        }


def main():
    """
    Main orchestrator workflow

    Returns:
        int: Exit code (0 = success, 1 = failure)
    """
    start_time = datetime.now()

    try:
        # Print banner and configuration
        print_banner()
        print_configuration()

        # Setup environment
        if not setup_environment():
            return 1

        # =============================================================================
        # STAGE 1: WEB SCRAPING
        # =============================================================================
        scraper_result = run_scraper()

        if not scraper_result['success']:
            logger.error("\n[ERROR] Pipeline failed at scraping stage")
            return 1

        # =============================================================================
        # STAGE 2: DATA PARSING
        # =============================================================================
        parser_result = run_parser(scraper_result['file_path'])

        if not parser_result['success']:
            logger.error("\n[ERROR] Pipeline failed at parsing stage")
            return 1

        # =============================================================================
        # STAGE 3: FILE GENERATION
        # =============================================================================
        generator_result = run_generator(parser_result['data'])

        if not generator_result['success']:
            logger.error("\n[ERROR] Pipeline failed at file generation stage")
            return 1

        # =============================================================================
        # PIPELINE COMPLETE
        # =============================================================================
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        log_section_header(logger, "PIPELINE COMPLETED SUCCESSFULLY")

        min_year = config.START_YEAR if config.START_YEAR is not None else config.DEFAULT_START_YEAR

        logger.info("\n[OK] All stages completed successfully!\n")
        logger.info("Summary:")
        logger.info(f"  Report:          {scraper_result['report_name']}")
        logger.info(f"  Data Filter:     {min_year} onwards")
        logger.info(f"  Parsed Rows:     {parser_result['row_count']}")
        logger.info(f"  Final Rows:      {generator_result['row_count']} (after consolidation)")
        logger.info(f"  DATA File:       {generator_result['data_file']}")
        logger.info(f"  META File:       {generator_result['meta_file']}")
        logger.info(f"  Duration:        {duration:.2f} seconds")
        logger.info(f"  Log File:        {config.LOG_FILEPATH}")

        print(f"\n{'='*70}")
        print("[OK] Pipeline completed successfully!")
        print(f"Check output folder: {config.LATEST_OUTPUT_DIR}")
        print(f"{'='*70}\n")

        return 0

    except KeyboardInterrupt:
        logger.warning("\n\n[WARNING] Pipeline interrupted by user (CTRL+C)")
        return 130

    except Exception as e:
        logger.error(f"\n[ERROR] Pipeline failed with unexpected error: {str(e)}", exc_info=True)
        return 1


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
