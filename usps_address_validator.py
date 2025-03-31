import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import requests
import keyring
import os

########################################################################
# USPS Endpoint & Keyring Constants
########################################################################
SERVICE_NAME = "usps_validator"    # Keyring service name
TOKEN_KEY    = "oauth_token"       # Under which we store the USPS OAuth token
CLIENT_ID_KEY = "client_id"        # We'll store client_id in keyring too
CLIENT_SECRET_KEY = "client_secret"

USPS_OAUTH_TOKEN_URL = "https://apis.usps.com/oauth2/v3/token"   # Production token endpoint
# For testing environment: USPS_OAUTH_TOKEN_URL = "https://apis-tem.usps.com/oauth2/v3/token"

USPS_ENDPOINT = "https://apis.usps.com/addresses/v3/address"     # The address standardization URL

########################################################################
# Keyring / Credential Management
########################################################################

def get_token():
    """Retrieve the currently stored OAuth access_token from keyring (if any)."""
    return keyring.get_password(SERVICE_NAME, TOKEN_KEY)

def set_token(token):
    """Store a new OAuth access_token in keyring."""
    keyring.set_password(SERVICE_NAME, TOKEN_KEY, token)

def get_client_id():
    """Retrieve the stored client_id from keyring."""
    return keyring.get_password(SERVICE_NAME, CLIENT_ID_KEY)

def set_client_id(cid):
    keyring.set_password(SERVICE_NAME, CLIENT_ID_KEY, cid)

def get_client_secret():
    """Retrieve the stored client_secret from keyring."""
    return keyring.get_password(SERVICE_NAME, CLIENT_SECRET_KEY)

def set_client_secret(sec):
    keyring.set_password(SERVICE_NAME, CLIENT_SECRET_KEY, sec)

########################################################################
# OAuth 2.0: Client Credentials Flow
########################################################################

def fetch_and_store_oauth_token():
    """
    1. Fetch client_id and client_secret from keyring.
    2. POST to the USPS /token endpoint with grant_type=client_credentials.
    3. If success, store the new 'access_token' in keyring so we can use it for /address calls.
    """
    cid = get_client_id()
    sec = get_client_secret()

    if not cid or not sec:
        messagebox.showerror("Error", "No client ID/secret found. Please set them first.")
        return

    data = {
        "grant_type": "client_credentials",
        "client_id": cid,
        "client_secret": sec,
        # Typically the scope is "addresses" according to the YAML
        "scope": "addresses",
    }

    try:
        resp = requests.post(USPS_OAUTH_TOKEN_URL, data=data, timeout=10)
        # Raise exception if 4xx or 5xx
        resp.raise_for_status()
    except requests.RequestException as e:
        messagebox.showerror("Error", f"Token request failed:\n{e}")
        return

    try:
        token_json = resp.json()
    except ValueError:
        messagebox.showerror("Error", "Token endpoint returned invalid JSON.")
        return

    access_token = token_json.get("access_token")
    if not access_token:
        messagebox.showerror("Error", f"No access_token in response:\n{token_json}")
        return

    # Store the token in keyring
    set_token(access_token)
    messagebox.showinfo("Success", f"Received OAuth token:\n{access_token[:60]}...")

########################################################################
# Address Validation Logic
########################################################################

def clean_zip(val):
    """
    Convert numeric or string ZIP codes to a proper digit string, 
    removing any .0 if present.
    """
    if pd.isna(val):
        return ""
    # If it's numeric, convert to an int then string
    if isinstance(val, (int, float)):
        return str(int(val))  # e.g. 63146.0 -> 63146
    # Otherwise, it's a string—strip whitespace
    s = str(val).strip()
    # Possibly remove .0 if present
    if s.endswith(".0"):
        s = s[:-2]
    return s

def build_address_params(row_dict):
    street_address = row_dict.get("streetAddress", "")
    state = row_dict.get("state", "")
    city  = row_dict.get("city", "")
    
    # Force numeric ZIP fields to digit strings
    zip_code = clean_zip(row_dict.get("ZIPCode", ""))
    zip_plus4 = clean_zip(row_dict.get("ZIPPlus4", ""))

    # Must have streetAddress and state
    if not street_address or not state:
        return None

    # Must have either city or ZIPCode
    if not city and not zip_code:
        return None

    params = {
        "streetAddress": street_address,
        "state": state,
    }
    if city:
        params["city"] = city
    if zip_code:
        params["ZIPCode"] = zip_code

    # Optional fields
    if "firm" in row_dict and row_dict["firm"]:
        params["firm"] = row_dict["firm"]
    if "secondaryAddress" in row_dict and row_dict["secondaryAddress"]:
        params["secondaryAddress"] = row_dict["secondaryAddress"]
    if zip_plus4:  # only if not empty
        params["ZIPPlus4"] = zip_plus4
    if "urbanization" in row_dict and row_dict["urbanization"]:
        params["urbanization"] = row_dict["urbanization"]

    return params

def validate_address(row_dict, token):
    """
    Call USPS /address endpoint. The row_dict may contain extra ID fields that
    we simply carry through to the final output.
    """
    params = build_address_params(row_dict)
    if not params:
        # The row is missing required fields
        return {
            **row_dict,
            "ValidationError": "Missing required fields (streetAddress/state/city-or-ZIPCode)"
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    try:
        resp = requests.get(USPS_ENDPOINT, params=params, headers=headers, timeout=10)
    except requests.RequestException as ex:
        return {**row_dict, "ValidationError": f"RequestException: {str(ex)}"}

    if resp.status_code != 200:
        return {**row_dict, "ValidationError": f"HTTP {resp.status_code}: {resp.text}"}

    # Parse JSON
    try:
        data = resp.json()
    except ValueError:
        return {**row_dict, "ValidationError": "Invalid JSON in response"}

    # Check for warnings or corrections
    if "warnings" in data and isinstance(data["warnings"], list):
        row_dict["Warnings"] = "; ".join(data["warnings"])

    address_data = data.get("address", {})

    # Build standardized fields
    standardized_fields = {
        "Standardized_Firm": data.get("firm", ""),
        "Standardized_StreetAddress": address_data.get("streetAddress", ""),
        "Standardized_StreetAddressAbbrev": address_data.get("streetAddressAbbreviation", ""),
        "Standardized_SecondaryAddress": address_data.get("secondaryAddress", ""),
        "Standardized_City": address_data.get("city", ""),
        "Standardized_CityAbbrev": address_data.get("cityAbbreviation", ""),
        "Standardized_State": address_data.get("state", ""),
        "Standardized_ZIPCode": address_data.get("ZIPCode", ""),
        "Standardized_ZIPPlus4": address_data.get("ZIPPlus4", ""),
        "Standardized_Urbanization": address_data.get("urbanization", ""),
    }

    # Additional info
    additional = data.get("additionalInfo", {})
    if additional:
        standardized_fields.update({
            "DeliveryPoint": additional.get("deliveryPoint", ""),
            "CarrierRoute": additional.get("carrierRoute", ""),
            "DPVConfirmation": additional.get("DPVConfirmation", ""),
            "DPVCMRA": additional.get("DPVCMRA", ""),
            "Business": additional.get("business", ""),
            "CentralDeliveryPoint": additional.get("centralDeliveryPoint", ""),
            "Vacant": additional.get("vacant", ""),
        })

    return {**row_dict, **standardized_fields}

########################################################################
# Main Processing
########################################################################

def process_file(file_path):
    token = get_token()
    if not token:
        messagebox.showerror("Error", "No USPS OAuth token found. Please get one first.")
        return

    # Read the Excel
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
    except Exception as e:
        messagebox.showerror("Error", f"Could not read the Excel file:\n{e}")
        return

    # Validate row-by-row
    results = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()

        # Optionally ensure ID fields exist
        row_dict.setdefault("RecordID", "")
        row_dict.setdefault("CustomerID", "")
        row_dict.setdefault("OtherID", "")

        validated = validate_address(row_dict, token)
        results.append(validated)

    out_df = pd.DataFrame(results)

    # Save
    base, ext = os.path.splitext(file_path)
    output_path = f"{base}_validated{ext}"
    try:
        out_df.to_excel(output_path, index=False)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save Excel file:\n{e}")
        return

    messagebox.showinfo("Success", f"Validated file saved as:\n{output_path}")

########################################################################
# GUI Setup
########################################################################

def update_client_credentials(client_id_entry, client_secret_entry):
    """
    Store client_id and client_secret in keyring. 
    (We won't get a token *immediately* in this function.)
    """
    cid = client_id_entry.get().strip()
    sec = client_secret_entry.get().strip()
    if not cid or not sec:
        messagebox.showerror("Error", "Client ID/Secret cannot be empty.")
        return
    set_client_id(cid)
    set_client_secret(sec)
    messagebox.showinfo("Success", "Client credentials stored. Now click 'Get OAuth Token'.")

def main():
    root = tk.Tk()
    root.title("USPS Addresses 3.0 Validator")

    # Inputs for client_id and client_secret
    tk.Label(root, text="USPS Client ID:").pack(pady=2)
    client_id_entry = tk.Entry(root, width=60)
    client_id_entry.pack(pady=2)

    tk.Label(root, text="USPS Client Secret:").pack(pady=2)
    client_secret_entry = tk.Entry(root, width=60, show="*")
    client_secret_entry.pack(pady=2)

    # Buttons
    tk.Button(root, text="Store Client Credentials",
              command=lambda: update_client_credentials(client_id_entry, client_secret_entry)).pack(pady=5)

    tk.Button(root, text="Get OAuth Token",
              command=fetch_and_store_oauth_token).pack(pady=5)

    tk.Button(root, text="Select Excel File to Validate",
              command=select_file).pack(pady=20)

    root.mainloop()

def select_file():
    file_path = filedialog.askopenfilename(
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    if file_path:
        process_file(file_path)

if __name__ == "__main__":
    main()
