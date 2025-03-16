"""DNRScraper class to scrape the Iowa DNR website for enforcement orders."""

import logging
import os
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scraper.config.config import CHROME_OPTIONS
from scraper.models.donr_scraper import ViolationType
from scraper.models.mappers.base import Base
from scraper.models.mappers.violation import Violation
from scraper.pdf_extractor.pdf_extractor import PDFExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DNRScraper:
    """Scraper class for extracting violation data from Iowa DNR website."""

    def __init__(
        self, db_path: str = "sqlite:///dnr_records.db", results_limit: int = 5
    ):
        """Initialize the DNRScraper object.

        Args:
            db_path: Database connection string.
            results_limit: Number of results to scrape
        """
        self.base_url = "https://programs.iowadnr.gov/documentsearch"
        self.search_url = f"{self.base_url}/Home/Search"
        self.results_limit = results_limit
        self.pdf_extractor = PDFExtractor()

        self._setup_database(db_path)
        self._setup_webdriver()

    def _setup_database(self, db_path: str):
        """Set up the database connection and create tables if they don't exist.

        Args:
            db_path: Database connection string.
        """
        self.engine = create_engine(
            db_path,
        )
        Base.metadata.create_all(self.engine)

        session = sessionmaker(bind=self.engine)
        self.db_sess = session()

    def _setup_webdriver(self):
        """Set up the Chrome webdriver."""
        options = Options()

        for option in CHROME_OPTIONS:
            options.add_argument(option)
        options.binary_location = "/usr/bin/chromium-browser"

        try:
            self.driver = webdriver.Chrome(options=options)
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            self._install_chrome_dependencies()
            self.driver = webdriver.Chrome(options=options)

    def _install_chrome_dependencies(self):
        """Install the necessary dependencies for Chrome."""
        os.system("sudo apt-get update")
        os.system("sudo apt-get install -y chromium-browser chromium-chromedriver")

    def search_documents(self) -> list[Violation]:
        """Search the documents and process the results.

        Returns:
            List of Violation objects.
        """
        try:
            self.driver.get(self.search_url)
            wait = WebDriverWait(self.driver, 10)

            program_select = wait.until(
                EC.presence_of_element_located((By.ID, "Program"))
            )
            Select(program_select).select_by_visible_text("Enforcement Orders")

            search_button = wait.until(
                EC.element_to_be_clickable((By.ID, "searchSubmit"))
            )
            search_button.click()

            return self._process_results(wait)

        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []

    def _process_results(self, wait):
        """Process the search results.

        Args:
            wait: WebDriverWait object.

        Returns:
            List of Violation objects.
        """
        results = []
        processed = 0
        page = 1

        wait.until(EC.presence_of_element_located((By.ID, "ResultsTable")))

        while processed < self.results_limit:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.find("table", {"id": "ResultsTable"})

            if not table:
                break

            for row in table.find_all("tr")[1:]:  # Skip header
                if processed >= self.results_limit:
                    break

                violation = self._process_row(row)
                if violation:
                    results.append(violation)
                    processed += 1

            if processed >= self.results_limit or not self._next_page(page):
                break
            page += 1

        return results[: self.results_limit]

    def _process_row(self, row):
        """Process a row in the results table.

        Args:
            row: BeautifulSoup row object.

        Returns:
            Violation object if successful, None otherwise.
        """
        try:
            cols = row.find_all("td")
            if len(cols) < 6:
                return None

            link_col = cols[0].find("a")
            if not link_col:
                return None

            download_url = f"{self.base_url}/Home/{link_col['href'].split('./')[-1]}"
            defendant = cols[5].text.strip()

            logger.info("=" * 50)
            logger.info(f"Processing document for {defendant}")
            logger.info(f"URL: {download_url}")

            text_data = self.pdf_extractor.extract_from_pdf(download_url)
            if not text_data:
                logger.error(f"Failed to extract text from PDF for {defendant}")
                return None

            # Logging this so it's easier to debug if the settlement isn't extracted
            # correctly, meaning we should expand the patterns in the config file.
            preview = text_data["text"].replace("\n", " ").strip()
            logger.info(f"Extracted text preview for {defendant}:\n{preview}\n")

            settlement = self.pdf_extractor.extract_settlement(text_data, download_url)

            if settlement is None:
                logger.warning(f"No settlement found for {defendant}")
            else:
                logger.info(f"Found settlement for {defendant}: ${settlement:,.2f}")

            violation = Violation(
                defendant=defendant,
                plaintiff="Iowa Department of Natural Resources",
                year=int(cols[2].text.strip().split("/")[2]),
                settlement=settlement,
                violation_type=ViolationType.ENVIRONMENTAL,
                data_source=self.search_url,
                link=download_url,
                notes=cols[4].text.strip(),
            )

            logger.info("Created record:")
            logger.info(f"Defendant: {violation.defendant}")
            logger.info(
                f"Settlement: ${violation.settlement:,.2f}"
                if violation.settlement
                else "Settlement: None"
            )

            return violation

        except Exception as exc:
            logger.error(f"Error processing row: {exc}")
            return None

    def _next_page(self, current_page):
        """Go to the next page of results.

        Args:
            current_page: Current page number.

        Returns:
            True if successful, False otherwise.
        """
        try:
            next_button = self.driver.find_element(
                By.CSS_SELECTOR, f"a[href*='page={current_page + 1}']"
            )
            next_button.click()
            time.sleep(2)

            return True
        except Exception:
            return False

    def save_records(self, violations: list[Violation]) -> None:
        """Save the records to the database.

        Args:
            violations: List of Violation objects.
        """
        try:
            successful = 0
            failed = 0
            null_settlements = 0

            logger.info(f"\nSaving {len(violations)} records:")

            for violation in violations:
                try:
                    if not self._record_exists(violation):
                        self.db_sess.add(violation)
                        if violation.settlement is None:
                            null_settlements += 1
                            logger.warning(
                                f"NULL SETTLEMENT: {violation.defendant} - "
                                f"{violation.link}"
                            )
                        else:
                            logger.info(
                                f"VALID SETTLEMENT: {violation.defendant} - "
                                f"${violation.settlement:,.2f}"
                            )
                        successful += 1
                    else:
                        logger.info(f"Existing record: {violation.defendant}")
                except Exception as e:
                    logger.error(f"Error saving {violation.defendant}: {e}")
                    failed += 1
                    continue

            self.db_sess.commit()

            logger.info("\nSummary:")
            logger.info(f"Total records processed: {len(violations)}")
            logger.info(f"Successfully saved: {successful}")
            logger.info(f"Failed to save: {failed}")
            logger.info(f"Records with null settlements: {null_settlements}")

        except Exception as e:
            logger.error(f"Error in batch save: {e}")
            self.db_sess.rollback()

    def _record_exists(self, violation):
        """Check if the record already exists in the database.

        Args:
            violation: Violation object.

        Returns:
            True if the record exists, False otherwise.
        """
        return bool(
            self.db_sess.query(Violation)
            .filter_by(
                defendant=violation.defendant, year=violation.year, link=violation.link
            )
            .first()
        )

    def run(self):
        """Run the scraper."""
        try:
            logger.info("Starting scraper...")
            violations = self.search_documents()
            if violations:
                self.save_records(violations)
            logger.info("Scraping completed.")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up the resources."""
        if hasattr(self, "driver"):
            self.driver.quit()
        if hasattr(self, "db_sess"):
            self.db_sess.close()
