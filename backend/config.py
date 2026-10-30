import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    WX_APPID = os.getenv("WX_APPID", "")
    WX_SECRET = os.getenv("WX_SECRET", "")
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:@localhost:3306/roll_call?charset=utf8mb4",
    )
    TOKEN_SECRET = os.getenv("TOKEN_SECRET", "dev-secret")


settings = Settings()