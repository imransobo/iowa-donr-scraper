"""Helper configuration file for the scraper."""

# I gathered some patterns while downloading the documents manually and
# inspecting them.
PENALTY_PATTERNS = [
    r"administrative penalty of \$?([\d,]+(?:\.\d{2})?)",
    r"pay an administrative penalty of \$?([\d,]+(?:\.\d{2})?)",
    r"pay a penalty of \$?([\d,]+(?:\.\d{2})?)",
    r"penalty of \$?([\d,]+(?:\.\d{2})?)",
    r"pay \$?([\d,]+(?:\.\d{2})?)",
    r"shall pay \$?([\d,]+(?:\.\d{2})?)",
    r"in the amount of \$?([\d,]+(?:\.\d{2})?)",
    r"assessed a penalty of \$?([\d,]+(?:\.\d{2})?)",
    r"civil penalty of \$?([\d,]+(?:\.\d{2})?)",
    r"total penalty of \$?([\d,]+(?:\.\d{2})?)",
    r"monetary penalty of \$?([\d,]+(?:\.\d{2})?)",
    r"penalties totaling \$?([\d,]+(?:\.\d{2})?)",
    r"stipulated penalty of \$?([\d,]+(?:\.\d{2})?)",
    r"agrees to pay \$?([\d,]+(?:\.\d{2})?)",
    r"shall be assessed \$?([\d,]+(?:\.\d{2})?)",
    r"penalty in the amount of \$?([\d,]+(?:\.\d{2})?)",
    r"pay a \$?([\d,]+(?:\.\d{2})?)",
    r"administrative penalty in the amount of \$?([\d,]+(?:\.\d{2})?)",
    r"administrative[\s\n]+penalty[\s\n]+of[\s\n]+\$?([\d,]+(?:\.\d{2})?)",
    (
        r"pay[\s\n]+an[\s\n]+administrative[\s\n]+penalty[\s\n]+"
        r"of[\s\n]+\$?([\d,]+(?:\.\d{2})?)"
    ),
    r"shall pay a \$?([S5\d,]+(?:\.\d{2})?)",
    r"pay a \$?([S5\d,]+(?:\.\d{2})?)",
    r"pay a \$?([S5\d,]+(?:\.\d{2})?)\s*(?:civil)?\s*penalty",
    r"shall pay.*?\$?([S5\d,]+(?:\.\d{2})?)",
]

SQLITE_CONFIG = {
    "connect_args": {
        "timeout": 30,
    }
}

DB_CONFIG = {"pool_recycle": 3600, "pool_pre_ping": True}

CHROME_OPTIONS = ["--headless", "--no-sandbox", "--disable-dev-shm-usage"]
