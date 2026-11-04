
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env
load_dotenv(BASE_DIR / ".env")


def get_connection():
    """
    Establish and return a MySQL database connection.
    """

    required_variables = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD"
    ]

    missing_variables = [
        variable
        for variable in required_variables
        if os.getenv(variable) is None
    ]

    if missing_variables:
        raise ValueError(
            f"Missing environment variables: {missing_variables}"
        )

    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    return connection
