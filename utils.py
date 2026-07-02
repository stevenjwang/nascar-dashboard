import json
import requests
from config import HEADERS

def fetch_json(url: str, timeout: int = 10) -> dict | list:
    """Fetches JSON data from a URL with basic error handling."""
    try:
        response = requests.get(url, timeout=timeout, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        return {"error": str(exc)}
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid JSON response: {exc}"}

def normalize_url(base_url: str, path: str) -> str:
    """Safely joins a base URL and a path."""
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"