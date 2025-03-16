"""Main module to run the scraper."""
import argparse
import logging

from scraper.dnr_scraper import DNRScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main function to run the scraper."""
    try:
        parser = argparse.ArgumentParser(
            description="Scrape violation data from Iowa DNR website"
        )
        parser.add_argument(
            "-l",
            "--limit",
            type=int,
            default=5,
            help="Number of results to scrape (default: 5)",
        )
        args = parser.parse_args()

        scraper = DNRScraper(results_limit=args.limit)
        scraper.run()
    except Exception as exc:
        logger.error(f"Scraper failed: {exc}")


if __name__ == "__main__":
    main()
