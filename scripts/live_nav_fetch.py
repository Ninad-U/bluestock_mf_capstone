import traceback
import requests
import pandas as pd

codes = {
    "HDFC_Top_100": "125497",
    "SBI_Bluechip": "119551",
    "ICICI_Bluechip": "120503",
    "Nippon_Large_Cap": "118632",
    "Axis_Bluechip": "119092",
    "Kotak_Bluechip": "120841"
}

# ----------------------------------------------------
# PATH DEFINITION
# ----------------------------------------------------

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

RAW_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------

try:
    for fund, code in codes.items():
        print(f"Fetching {fund} ({code})...")

        url = f"https://api.mfapi.in/mf/{code}"
        response = requests.get(url)

        print(f"Status Code: {response.status_code}")

        response.raise_for_status()

        data = response.json()

        nav_data = pd.DataFrame(data["data"])

        output_file = RAW_DIR / f"{fund}_nav.csv"
        nav_data.to_csv(output_file, index=False)

        print(f"Saved: {output_file}")
        print(f"Shape: {nav_data.shape}\n")

except Exception:
    print("\nAn error occurred:\n")
    traceback.print_exc()

finally:
    input("\nPress Enter to exit...")