import os
import requests
from dotenv import load_dotenv

load_dotenv()

POWER_AUTOMATE_URL = os.getenv("POWER_AUTOMATE_URL")


def send_email(to: str, subject: str, body: str):
    if not POWER_AUTOMATE_URL:
        print("POWER_AUTOMATE_URL not found in .env")
        return False

    payload = {
        "to": to,
        "subject": subject,
        "body": body
    }

    try:
        response = requests.post(
            POWER_AUTOMATE_URL,
            json=payload,
            timeout=10
        )

        print("Email response:", response.status_code, response.text)

        return response.status_code in [200, 202]

    except Exception as e:
        print("Email error:", e)
        return False