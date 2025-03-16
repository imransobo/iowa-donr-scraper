# Iowa DNR Violation Scraper
A Python web scraper that extracts environmental violation and settlement data from the Iowa Department of Natural Resources (DNR) website.


# Overview
This project automates the collection of environmental violation data from the Iowa DNR's document search system. It:
- Scrapes enforcement orders.
- Extracts settlement amounts using OCR and text processing.
- Stores the data in a SQLite database (can be improved if decided to be deployed).
- Handles various document formats and OCR challenges.

# Features
- Automated Web Navigation: Uses Selenium to navigate the DNR's search interface 
### PDF Processing:
1. Primary extraction using pdfplumber.
2. Fallback to OCR using pytesseract for problematic PDFs. Handles common OCR errors (e.g., "S" vs "5").
3. Data Persistence: SQLite database with SQLAlchemy ORM.
4. Configurable: Adjustable search patterns and scraping limits.

# Installation
```` 
git clone [repository-url]
cd iowa-donr-scraper-imran-sobo

pip install -r requirements.txt

sudo apt-get update
sudo apt-get install -y chromium-browser chromium-chromedriver tesseract-ocr

python -m scraper.main --limit 5
````

##### By default, it processes 5 records. Modify the limit through the command line if needed.


## Author
#### Imran Sobo
