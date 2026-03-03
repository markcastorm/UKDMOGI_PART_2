"""
Web Scraper for UKDMOGI Part 2
Redemption Details of Redeemed Gilts

Handles:
- Browser automation with Selenium
- Cookie consent acceptance
- Excel file download
- Download verification

Based on CHEF_NOVARTIS architecture
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service as ChromeService

import config
from logger_setup import setup_logger

# Initialize logger
logger = setup_logger(__name__)


class UKDMOScraper:
    """
    Web scraper for UK Debt Management Office Part 2 data

    Simplified scraper for Part 2 - no date selection needed,
    just download all historical redemption data.
    """

    def __init__(self):
        """Initialize scraper with Chrome WebDriver"""
        self.driver = None
        self.download_dir = str(config.DOWNLOADS_DIR.absolute())

        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)

        logger.info("UKDMOScraper initialized")
        logger.debug(f"Download directory: {self.download_dir}")

    def setup_driver(self):
        """
        Setup Chrome WebDriver with appropriate options

        Returns:
            webdriver.Chrome: Configured Chrome WebDriver
        """
        logger.info("Setting up Chrome WebDriver...")

        # Chrome options
        chrome_options = webdriver.ChromeOptions()

        # Headless mode (optional)
        if config.HEADLESS_MODE:
            chrome_options.add_argument("--headless=new")
            logger.debug("Headless mode enabled")

        # Download preferences
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False  # Disable safe browsing warnings
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # Additional options for stability
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Create driver
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("[OK] Chrome WebDriver initialized")
            return self.driver

        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {str(e)}")
            raise

    def handle_cookie_consent(self):
        """
        Handle cookie consent banner if present

        Returns:
            bool: True if handled, False if not found (which is OK)
        """
        logger.info("Checking for cookie consent banner...")

        try:
            # Wait for cookie consent button
            cookie_button = WebDriverWait(self.driver, config.COOKIE_WAIT_TIMEOUT).until(
                EC.element_to_be_clickable((By.ID, config.COOKIE_CONSENT_BUTTON_ID))
            )

            logger.debug(f"Cookie consent button found: {config.COOKIE_CONSENT_BUTTON_ID}")

            # Click the button
            cookie_button.click()
            logger.info("[OK] Cookie consent accepted")

            # Wait a moment for banner to disappear
            time.sleep(1)

            return True

        except TimeoutException:
            logger.warning("Cookie consent button not found (may have been accepted previously)")
            return False

        except Exception as e:
            logger.warning(f"Error handling cookie consent: {str(e)}")
            return False

    def click_excel_download(self):
        """
        Click Excel download button to trigger file download

        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Looking for Excel download button...")

        try:
            # Wait for Excel button to be clickable
            excel_button = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, config.EXCEL_BUTTON_XPATH))
            )

            logger.debug("Excel button found")

            # Scroll button into view (in case it's not visible)
            self.driver.execute_script("arguments[0].scrollIntoView(true);", excel_button)
            time.sleep(0.5)

            # Click the button
            excel_button.click()
            logger.info("[OK] Excel download button clicked")

            return True

        except TimeoutException:
            logger.error("Excel download button not found within timeout period")
            return False

        except ElementClickInterceptedException:
            # Try JavaScript click if normal click is intercepted
            logger.warning("Normal click intercepted, trying JavaScript click...")
            try:
                excel_button = self.driver.find_element(By.XPATH, config.EXCEL_BUTTON_XPATH)
                self.driver.execute_script("arguments[0].click();", excel_button)
                logger.info("[OK] Excel download triggered via JavaScript")
                return True
            except Exception as js_error:
                logger.error(f"JavaScript click also failed: {str(js_error)}")
                return False

        except Exception as e:
            logger.error(f"Failed to click Excel button: {str(e)}")
            return False

    def wait_for_download(self, timeout=None):
        """
        Wait for file download to complete

        Args:
            timeout: Maximum wait time in seconds (default from config)

        Returns:
            str: Path to downloaded file, or None if timeout
        """
        if timeout is None:
            timeout = config.DOWNLOAD_WAIT_TIMEOUT

        logger.info(f"Waiting for file download (timeout: {timeout}s)...")

        start_time = time.time()

        while time.time() - start_time < timeout:
            # Look for .xls or .xlsx files (not .crdownload or .tmp)
            files = os.listdir(self.download_dir)

            # Filter for complete Excel files
            complete_files = [
                os.path.join(self.download_dir, f)
                for f in files
                if f.endswith(('.xls', '.xlsx')) and not f.endswith('.crdownload')
            ]

            if complete_files:
                downloaded_file = complete_files[0]
                file_size = os.path.getsize(downloaded_file)

                # Validate file size
                if file_size >= config.MIN_FILE_SIZE:
                    logger.info(f"[OK] Download complete: {os.path.basename(downloaded_file)}")
                    logger.debug(f"File size: {file_size:,} bytes")
                    return downloaded_file
                else:
                    logger.warning(f"Downloaded file too small: {file_size} bytes")

            time.sleep(1)

        logger.error(f"Download timeout after {timeout} seconds")
        return None

    def scrape_part2(self):
        """
        Main scraping workflow for Part 2

        Returns:
            dict: Result dictionary with success status and file path
                  {
                      "success": bool,
                      "file_path": str,
                      "error": str,
                      "report_name": str
                  }
        """
        result = {
            "success": False,
            "file_path": None,
            "error": None,
            "report_name": config.PART2_REPORT_NAME
        }

        try:
            logger.info(f"Starting Part 2 scraping: {config.PART2_REPORT_NAME}")
            logger.info(f"URL: {config.PART2_URL}")

            # Setup driver
            self.setup_driver()

            # Navigate to URL
            logger.info("Navigating to DMO website...")
            self.driver.get(config.PART2_URL)
            logger.info("[OK] Page loaded")

            # Handle cookie consent
            self.handle_cookie_consent()

            # Wait for page to fully load
            time.sleep(2)

            # Click Excel download button
            if not self.click_excel_download():
                result["error"] = "Failed to trigger Excel download"
                return result

            # Wait for download to complete
            downloaded_file = self.wait_for_download()

            if not downloaded_file:
                result["error"] = "Download timeout or failed"
                return result

            # Success!
            result["success"] = True
            result["file_path"] = downloaded_file

            logger.info("[OK] Part 2 scraping completed successfully")
            return result

        except Exception as e:
            logger.error(f"Scraping failed: {str(e)}", exc_info=True)
            result["error"] = str(e)
            return result

        finally:
            # Always close the browser
            if self.driver:
                logger.debug("Closing browser...")
                self.driver.quit()
                logger.info("[OK] Browser closed")


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("\nTesting scraper.py module...\n")

    # Create scraper instance
    scraper = UKDMOScraper()

    # Run scraping
    result = scraper.scrape_part2()

    # Print results
    print("\n" + "="*70)
    print("SCRAPING RESULTS")
    print("="*70)
    print(f"Success: {result['success']}")
    print(f"Report: {result['report_name']}")

    if result['success']:
        print(f"Downloaded file: {result['file_path']}")
        print(f"File size: {os.path.getsize(result['file_path']):,} bytes")
    else:
        print(f"Error: {result['error']}")

    print("="*70)
