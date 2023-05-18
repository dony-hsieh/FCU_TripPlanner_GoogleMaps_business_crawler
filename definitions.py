from pathlib import Path

# database environment setting
DOTENV = ".env"
ENVVAR_KEY = ["TPD_HOST", "TPD_PORT", "TPD_USER", "TPD_PASSWORD", "TPD_DB"]

CRAWLED_BUSINESS_DATA_FIELDS = [
    "name",
    "rating",
    "total_reviews",
    "place_type",
    "website",
    "opening_hours",
    "map"
]

CRAWLED_DATA_STORE_PATH = str(Path("business_data/").absolute())