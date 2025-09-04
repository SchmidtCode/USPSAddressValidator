# USPS Address Validator (Addresses 3.0) Python Excel

A simple Python/Tkinter application for validating and standardizing USPS addresses using the USPS Addresses 3.0 API. This tool reads addresses from an Excel file, sends them to the USPS API, and saves a new Excel file with standardized addresses appended.

## Features

- **Tkinter GUI**: Simple user interface to select an Excel file and configure the USPS OAuth token.
- **Keyring Integration**: Securely store and retrieve the USPS OAuth token on your system.
- **Handles Required/Optional Fields**: Complies with USPS’s requirement for `streetAddress`, `state`, and either `city` or `ZIPCode`. Also supports optional fields like `firm`, `secondaryAddress`, `urbanization`, and `ZIPPlus4`.
- **ID Fields**: Pass along up to three ID fields (or more if needed) without sending them to the USPS API, purely for user reference in the output.
- **Output**: Creates a new Excel file (original name + `_validated.xlsx`) containing the original columns plus standardized columns (e.g., `Standardized_StreetAddress`, `Standardized_City`, etc.).

## Getting Started

### Prerequisites

- Python 3.13
- [uv](https://docs.astral.sh/uv/) (fast Python package/dependency manager)
- A valid USPS Addresses 3.0 OAuth token

> **Note:** `tkinter` comes with most Python distributions. On Linux, you may need to install it separately (`sudo apt install python3-tk` on Debian/Ubuntu).

### Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/your-username/usps-address-validator.git
   cd usps-address-validator
   ```

2. **Create a virtual environment** (managed by uv):

   ```bash
   uv venv
   ```

3. **Install dependencies**:

   ```bash
   uv sync
   ```

   This will install:

   - `pandas`
   - `openpyxl`
   - `requests`
   - `keyring`

### Usage

1. **Run the application**:

   ```bash
   uv run python usps_address_validator.py
   ```

2. **Enter your USPS OAuth token** in the text field (the script uses `keyring` to store it securely).

3. **Click "Update Token"** to save the token in your system keyring.

4. **Click "Select Excel File to Validate"** and choose an Excel file containing the addresses.

After the script completes, you’ll see a popup indicating success and showing the path to your validated file (e.g. `myAddresses_validated.xlsx`).

### Example Input File

Here’s a typical row structure your Excel might have:

| RecordID | CustomerID | OtherID | firm       | streetAddress     | secondaryAddress | city      | state | ZIPCode | ZIPPlus4 | urbanization |  
|----------|-----------|---------|------------|-------------------|------------------|-----------|-------|--------|---------|------------|  
| 1001     | 10        | ABC123  | Some Firm  | 123 Main Street   | Suite 200        | Anytown   | NC    | 12345   | 6789     |            |  
| 1002     | 11        | XYZ999  |            | 9876 Maple Ave    |                  | Newville  | VA    |        |         |            |  
| 1003     | 12        | ABC444  | John Corp  | 25 Paseo del Río  | Apt 3B           |          | PR    | 00907   |         | Río Piedras|  

- **ID fields**: `RecordID`, `CustomerID`, `OtherID`  
- **Required**: `streetAddress`, `state`, and at least `city` or `ZIPCode`  
- **Optional**: `firm`, `secondaryAddress`, `ZIPPlus4`, `urbanization`  

If a row is missing a required field (e.g., `state`), you’ll see a `ValidationError` in the output.

### Example Output File

In the validated file (`*_validated.xlsx`), you’ll see your original columns plus new standardized columns such as:

- `Standardized_StreetAddress`
- `Standardized_City`
- `Standardized_State`
- `Standardized_ZIPCode`
- `Standardized_ZIPPlus4`
- `ValidationError`
- `Warnings`
- etc.

### FAQ

**Q: How do I get a USPS OAuth token?**  
A: Sign up for a USPS Web Tools developer account on the [USPS Developer Portal](https://www.usps.com/business/web-tools-apis/) and request access to the Addresses 3.0 API.

**Q: Do I need city & state if I have the ZIPCode?**  
A: USPS requires at least `streetAddress` & `state` and **one** of `city` or `ZIPCode`. If `city` is missing, you must include `ZIPCode`; if `ZIPCode` is missing, you must include `city`.

**Q: How do I store the token if I don’t want to use keyring?**  
A: The code uses `keyring` for convenience. If you prefer a different storage, you can modify the `get_token()` and `set_token()` functions.

## Contributing

1. Fork this repository
2. Create a new feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add an amazing feature'`)
4. Push to your branch (`git push origin feature/amazing-feature`)
5. Create a new Pull Request

## License

This project is licensed under the [MIT License](LICENSE).
