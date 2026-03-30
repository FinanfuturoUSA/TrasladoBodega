from os import getenv
from dotenv import load_dotenv

load_dotenv()


class Config:
    siigo_api_user = str(getenv("SIIGO_API_USER", ""))
    siigo_api_key = str(getenv("SIIGO_API_KEY", ""))
    partner_id = str(getenv("PARTNER_ID", "finanfuturo"))
    local_timezone = str(getenv("LOCAL_TIMEZONE", "America/Bogota"))
