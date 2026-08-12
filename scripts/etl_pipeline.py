"""
ETL pipeline for Bluestock Mutual Fund Analytics Capstone

Extract raw CSV datasets, clean and validate the data,
save cleaned datasets, and load them into SQLite.
"""

import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path
import time
import sys

PAUSE_ON_EXIT = False

# ============================================================
# Project paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DB_PATH = BASE_DIR / "data" / "db" / "bluestock_mf.db"


# ============================================================
# Dataset configuration
# ============================================================

DATASETS = {

    "fund_master": {
        "date_columns": ["launch_date"],
        "date_formats": {"launch_date": "%Y-%m-%d"},
        "date_month_columns": [],  # Columns that are YYYY-MM format
        "numeric_columns": [
            "amfi_code",
            "expense_ratio_pct",
            "exit_load_pct",
            "min_sip_amount",
            "min_lumpsum_amount"
        ]
    },

    "nav_history": {
        "date_columns": ["date"],
        "date_formats": {"date": "%Y-%m-%d"},
        "date_month_columns": [],
        "numeric_columns": [
            "amfi_code",
            "nav"
        ]
    },

    "aum_by_fund_house": {
        "date_columns": ["date"],
        "date_formats": {"date": "%Y-%m-%d"},
        "date_month_columns": [],
        "numeric_columns": [
            "aum_lakh_crore",
            "aum_crore",
            "num_schemes"
        ]
    },

    "monthly_sip_inflows": {
        "date_columns": ["month"],
        "date_formats": {"month": "%Y-%m"},  # YYYY-MM format
        "date_month_columns": ["month"],      # These columns need to be converted to YYYY-MM-DD
        "numeric_columns": [
            "sip_inflow_crore",
            "active_sip_accounts_crore",
            "new_sip_accounts_lakh",
            "sip_aum_lakh_crore",
            "yoy_growth_pct"
        ]
    },

    "category_inflows": {
        "date_columns": ["month"],
        "date_formats": {"month": "%Y-%m"},  # YYYY-MM format
        "date_month_columns": ["month"],      # These columns need to be converted to YYYY-MM-DD
        "numeric_columns": [
            "net_inflow_crore"
        ]
    },

    "industry_folio_count": {
        "date_columns": ["month"],
        "date_formats": {"month": "%Y-%m"},  # YYYY-MM format
        "date_month_columns": ["month"],      # These columns need to be converted to YYYY-MM-DD
        "numeric_columns": [
            "total_folios_crore",
            "equity_folios_crore",
            "debt_folios_crore",
            "hybrid_folios_crore",
            "others_folios_crore"
        ]
    },

    "scheme_performance": {
        "date_columns": [],
        "date_formats": {},
        "date_month_columns": [],
        "numeric_columns": [
            "amfi_code",
            "return_1yr_pct",
            "return_3yr_pct",
            "return_5yr_pct",
            "benchmark_3yr_pct",
            "alpha",
            "beta",
            "sharpe_ratio",
            "sortino_ratio",
            "std_dev_ann_pct",
            "max_drawdown_pct",
            "aum_crore",
            "expense_ratio_pct",
            "morningstar_rating"
        ]
    },

    "investor_transactions": {
        "date_columns": ["transaction_date"],
        "date_formats": {"transaction_date": "%Y-%m-%d"},
        "date_month_columns": [],
        "numeric_columns": [
            "amount_inr",
            "annual_income_lakh"
        ]
    },

    "portfolio_holdings": {
        "date_columns": ["portfolio_date"],
        "date_formats": {"portfolio_date": "%Y-%m-%d"},
        "date_month_columns": [],
        "numeric_columns": [
            "amfi_code",
            "weight_pct",
            "market_value_cr",
            "current_price_inr"
        ]
    },

    "benchmark_indices": {
        "date_columns": ["date"],
        "date_formats": {"date": "%Y-%m-%d"},
        "date_month_columns": [],
        "numeric_columns": [
            "close_value"
        ]
    }
}


# ============================================================
# Extract
# ============================================================

def extract_dataset(name):
    """Read a raw CSV dataset."""

    path = RAW_DIR / f"{name}.csv"

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}"
        )

    return pd.read_csv(path)


# ============================================================
# Invalid date reporting
# ============================================================

def report_invalid_dates(df, column, dataset_name, amfi_column=None, nav_column=None):
    """
    Report detailed diagnostics for invalid dates.
    """
    invalid_mask = df[column].isna()
    invalid_df = df[invalid_mask].copy()
    
    print()
    print("=" * 70)
    print("INVALID DATE DIAGNOSTICS")
    print("=" * 70)
    print(f"Dataset: {dataset_name}")
    print(f"Column: {column}")
    print(f"Number of invalid rows: {len(invalid_df)}")
    
    if len(invalid_df) > 0:
        print()
        print("Sample invalid records (up to 100):")
        
        # Create report columns
        report_cols = ["index"]
        if amfi_column and amfi_column in df.columns:
            report_cols.append(amfi_column)
        report_cols.append(column)
        if nav_column and nav_column in df.columns:
            report_cols.append(nav_column)
        
        # Get raw values from original CSV
        # Try to read raw file to show original values
        try:
            raw_path = RAW_DIR / f"{dataset_name}.csv"
            if raw_path.exists():
                raw_df = pd.read_csv(raw_path, dtype={column: "string"})
                if column in raw_df.columns:
                    # Show sample of raw values
                    print()
                    print("Raw date values (sample):")
                    for idx in invalid_df.head(100).index:
                        if idx < len(raw_df):
                            raw_val = raw_df.loc[idx, column] if column in raw_df.columns else "N/A"
                            print(f"Row {idx}: {repr(raw_val)}")
        except Exception:
            pass
        
        # Show DataFrame view
        print()
        print("DataFrame view (sample):")
        display_df = invalid_df.head(100).reset_index()
        print(display_df.to_string(index=False))
        
        if amfi_column and amfi_column in invalid_df.columns:
            print()
            print("Affected AMFI codes:")
            print(invalid_df[amfi_column].value_counts().head(20).to_string())
    
    return invalid_df


# ============================================================
# NAV handling
# ============================================================

def handle_nav_dates(df):
    """
    Create continuous daily dates separately for each fund
    and forward-fill NAV values across weekends/holidays.
    
    Returns: DataFrame with amfi_code, date, nav columns only
    """
    
    # --------------------------------------------------------
    # Validate dates before reindexing
    # --------------------------------------------------------
    
    invalid_dates = df[df["date"].isna()]
    
    if len(invalid_dates) > 0:
        # This should have been caught earlier, but just in case
        raise ValueError(
            f"nav_history: invalid or missing dates found "
            f"({len(invalid_dates)} rows). Run with detailed "
            f"date validation enabled for diagnostics."
        )
    
    # --------------------------------------------------------
    # Remove exact duplicates first
    # --------------------------------------------------------
    
    exact_duplicates = df.duplicated().sum()
    if exact_duplicates > 0:
        print(f"Removing {exact_duplicates} exact duplicate rows from nav_history")
        df = df.drop_duplicates()
    
    # --------------------------------------------------------
    # Check for duplicate fund/date combinations
    # --------------------------------------------------------
    
    duplicate_fund_dates = df[
        df.duplicated(subset=["amfi_code", "date"], keep=False)
    ]
    
    if len(duplicate_fund_dates) > 0:
        print()
        print("=" * 70)
        print("DUPLICATE AMFI CODE + DATE FOUND")
        print("=" * 70)
        print(f"Number of duplicate rows: {len(duplicate_fund_dates)}")
        print()
        print("Sample duplicate records:")
        print(duplicate_fund_dates.head(50).to_string(index=False))
        
        raise ValueError(
            "nav_history: duplicate AMFI code + date combinations found. "
            "Cannot automatically resolve. Please fix the source data."
        )
    
    result = []
    
    # --------------------------------------------------------
    # Process each fund separately
    # --------------------------------------------------------
    
    for amfi_code, fund_nav in df.groupby("amfi_code"):
        
        fund_nav = fund_nav.sort_values(
            "date"
        ).copy()
        
        # ----------------------------------------------------
        # Create complete daily date range
        # ----------------------------------------------------
        
        full_dates = pd.date_range(
            start=fund_nav["date"].min(),
            end=fund_nav["date"].max(),
            freq="D"
        )
        
        # ----------------------------------------------------
        # Reindex to complete daily dates
        # ----------------------------------------------------
        
        fund_nav = (
            fund_nav
            .set_index("date")
            .reindex(full_dates)
        )
        
        # ----------------------------------------------------
        # Restore AMFI code
        # ----------------------------------------------------
        
        fund_nav["amfi_code"] = amfi_code
        
        # ----------------------------------------------------
        # Forward-fill NAV
        # ----------------------------------------------------
        
        fund_nav["nav"] = (
            fund_nav["nav"]
            .ffill()
        )
        
        # ----------------------------------------------------
        # Restore date column
        # ----------------------------------------------------
        
        fund_nav.index.name = "date"
        
        result.append(
            fund_nav.reset_index()
        )
    
    # --------------------------------------------------------
    # Combine all funds
    # --------------------------------------------------------
    
    result_df = pd.concat(
        result,
        ignore_index=True
    )
    
    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------
    
    result_df = result_df.sort_values(
        ["amfi_code", "date"]
    ).reset_index(drop=True)
    
    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------
    
    if result_df["date"].isna().any():
        raise ValueError(
            "nav_history: missing dates remain after forward-fill."
        )
    
    if result_df["nav"].isna().any():
        raise ValueError(
            "nav_history: missing NAV values remain after forward-fill."
        )
    
    if (result_df["nav"] <= 0).any():
        non_positive = result_df[result_df["nav"] <= 0]
        print()
        print("=" * 70)
        print("NON-POSITIVE NAV VALUES")
        print("=" * 70)
        print(f"Number of non-positive NAV rows: {len(non_positive)}")
        print()
        print("Sample records:")
        print(non_positive.head(50).to_string(index=False))
        raise ValueError(
            "nav_history: non-positive NAV values remain after forward-fill."
        )
    
    # Ensure only the required columns are returned
    # Keep only amfi_code, date, nav
    result_df = result_df[["amfi_code", "date", "nav"]]
    
    return result_df


# ============================================================
# Investor transactions validation
# ============================================================

def validate_investor_transactions(df):
    """
    Validate and clean investor transactions dataset.
    """
    
    # --------------------------------------------------------
    # Standardise transaction_type
    # --------------------------------------------------------
    
    if "transaction_type" in df.columns:
        # Clean and standardise
        df["transaction_type"] = (
            df["transaction_type"]
            .str.strip()
            .str.title()
        )
        
        # Define valid types
        valid_types = {"Sip", "Lumpsum", "Redemption"}
        
        # Map variations to standard values
        type_mapping = {
            "Sip": "SIP",
            "Sips": "SIP",
            "Sip Investment": "SIP",
            "Systematic Investment Plan": "SIP",
            "Lumpsum": "Lumpsum",
            "Lump Sum": "Lumpsum",
            "LumpSum": "Lumpsum",
            "One Time": "Lumpsum",
            "Redemption": "Redemption",
            "Redeem": "Redemption",
            "Withdrawal": "Redemption"
        }
        
        df["transaction_type"] = df["transaction_type"].map(type_mapping).fillna(df["transaction_type"])
        
        # Check for unexpected values
        unexpected = df[~df["transaction_type"].isin(["SIP", "Lumpsum", "Redemption"])]
        
        if len(unexpected) > 0:
            print()
            print("=" * 70)
            print("UNEXPECTED TRANSACTION TYPES")
            print("=" * 70)
            print(f"Number of unexpected transaction types: {len(unexpected)}")
            print()
            print("Unexpected values:")
            print(unexpected["transaction_type"].value_counts().to_string())
            print()
            print("Sample records:")
            print(unexpected.head(20).to_string(index=False))
            
            raise ValueError(
                f"investor_transactions: {len(unexpected)} unexpected transaction types found. "
                "Please fix the source data."
            )
    
    # --------------------------------------------------------
    # Validate amount > 0
    # --------------------------------------------------------
    
    if "amount_inr" in df.columns:
        invalid_amount = df[
            df["amount_inr"].isna() |
            (df["amount_inr"] <= 0)
        ]
        
        if len(invalid_amount) > 0:
            print()
            print("=" * 70)
            print("INVALID AMOUNTS")
            print("=" * 70)
            print(f"Number of invalid amounts: {len(invalid_amount)}")
            print()
            print("Sample records:")
            print(invalid_amount.head(20).to_string(index=False))
            
            raise ValueError(
                f"investor_transactions: {len(invalid_amount)} invalid amounts found. "
                "Amount must be numeric and > 0."
            )
    
    # --------------------------------------------------------
    # Validate KYC status
    # --------------------------------------------------------
    
    if "kyc_status" in df.columns:
        df["kyc_status"] = df["kyc_status"].str.strip().str.upper()
        
        valid_kyc = {"VERIFIED", "PENDING", "NOT SUBMITTED", "COMPLIANT", "REJECTED"}
        
        unexpected_kyc = df[~df["kyc_status"].isin(valid_kyc)]
        
        if len(unexpected_kyc) > 0:
            print()
            print("=" * 70)
            print("UNEXPECTED KYC STATUS VALUES")
            print("=" * 70)
            print(f"Number of unexpected KYC status values: {len(unexpected_kyc)}")
            print()
            print("Unexpected values:")
            print(unexpected_kyc["kyc_status"].value_counts().to_string())
            print()
            print("Sample records:")
            print(unexpected_kyc.head(20).to_string(index=False))
            
            raise ValueError(
                f"investor_transactions: {len(unexpected_kyc)} unexpected KYC status values found. "
                "Valid values: VERIFIED, PENDING, NOT SUBMITTED, COMPLIANT, REJECTED"
            )
    
    return df


# ============================================================
# Scheme performance validation
# ============================================================

def validate_scheme_performance(df):
    """
    Validate scheme performance dataset.
    """
    
    # --------------------------------------------------------
    # Validate return columns are numeric
    # --------------------------------------------------------
    
    return_columns = [
        "return_1yr_pct",
        "return_3yr_pct",
        "return_5yr_pct",
        "benchmark_3yr_pct"
    ]
    
    for col in return_columns:
        if col in df.columns:
            non_numeric = df[pd.to_numeric(df[col], errors="coerce").isna() & df[col].notna()]
            
            if len(non_numeric) > 0:
                print()
                print("=" * 70)
                print(f"NON-NUMERIC VALUES IN {col.upper()}")
                print("=" * 70)
                print(f"Number of non-numeric values: {len(non_numeric)}")
                print()
                print("Sample records:")
                print(non_numeric[[col] + ["amfi_code"] if "amfi_code" in df.columns else [col]].head(20).to_string(index=False))
                
                raise ValueError(
                    f"scheme_performance: {len(non_numeric)} non-numeric values found in {col}."
                )
    
    # --------------------------------------------------------
    # Flag negative Sharpe ratios (report but don't modify)
    # --------------------------------------------------------
    
    if "sharpe_ratio" in df.columns:
        negative_sharpe = df[df["sharpe_ratio"] < 0]
        
        if len(negative_sharpe) > 0:
            print()
            print("=" * 70)
            print("NEGATIVE SHARPE RATIOS DETECTED")
            print("=" * 70)
            print(f"Number of negative Sharpe ratios: {len(negative_sharpe)}")
            print("(These will be flagged but not modified)")
            print()
            print("Sample records:")
            print(negative_sharpe[["amfi_code", "sharpe_ratio"] if "amfi_code" in df.columns else ["sharpe_ratio"]].head(20).to_string(index=False))
            
            # Add a flag column
            df["negative_sharpe_flag"] = df["sharpe_ratio"] < 0
    
    # --------------------------------------------------------
    # Validate expense ratio range (0.1% - 2.5%)
    # --------------------------------------------------------
    
    if "expense_ratio_pct" in df.columns:
        out_of_range = df[
            ~df["expense_ratio_pct"].isna() &
            ((df["expense_ratio_pct"] < 0.1) | (df["expense_ratio_pct"] > 2.5))
        ]
        
        if len(out_of_range) > 0:
            print()
            print("=" * 70)
            print("EXPENSE RATIO OUT OF RANGE")
            print("=" * 70)
            print(f"Number of expense ratios out of range (0.1% - 2.5%): {len(out_of_range)}")
            print()
            print("Sample records:")
            display_cols = ["amfi_code", "expense_ratio_pct"] if "amfi_code" in df.columns else ["expense_ratio_pct"]
            print(out_of_range[display_cols].head(20).to_string(index=False))
            
            raise ValueError(
                f"scheme_performance: {len(out_of_range)} expense ratios out of range (0.1% - 2.5%). "
                "Please fix the source data."
            )
    
    return df


# ============================================================
# AMFI code cross-validation
# ============================================================

def validate_amfi_codes():
    """
    Validate that all AMFI codes in fund_master exist in nav_history.
    """
    
    print()
    print("=" * 70)
    print("AMFI CODE CROSS-VALIDATION")
    print("=" * 70)
    
    # Load cleaned datasets
    fund_master_path = PROCESSED_DIR / "fund_master_cleaned.csv"
    nav_history_path = PROCESSED_DIR / "nav_history_cleaned.csv"
    
    if not fund_master_path.exists():
        raise FileNotFoundError(
            f"fund_master_cleaned.csv not found at {fund_master_path}"
        )
    
    if not nav_history_path.exists():
        raise FileNotFoundError(
            f"nav_history_cleaned.csv not found at {nav_history_path}"
        )
    
    fund_master = pd.read_csv(fund_master_path)
    nav_history = pd.read_csv(nav_history_path)
    
    # Get unique AMFI codes
    fund_codes = set(fund_master["amfi_code"].dropna().astype(int))
    nav_codes = set(nav_history["amfi_code"].dropna().astype(int))
    
    # Find missing codes
    missing_codes = fund_codes - nav_codes
    
    if missing_codes:
        print()
        print("=" * 70)
        print("ERROR: MISSING AMFI CODES IN NAV HISTORY")
        print("=" * 70)
        print(f"Total AMFI codes in fund_master: {len(fund_codes)}")
        print(f"Total AMFI codes in nav_history: {len(nav_codes)}")
        print(f"Missing codes in nav_history: {len(missing_codes)}")
        print()
        print("Missing AMFI codes:")
        missing_list = sorted(missing_codes)
        for i, code in enumerate(missing_list, 1):
            print(f"  {i}. {code}")
        
        # Show sample records from fund_master for missing codes
        print()
        print("Sample records from fund_master for missing codes:")
        missing_df = fund_master[fund_master["amfi_code"].isin(missing_codes)]
        print(missing_df.head(20).to_string(index=False))
        
        raise ValueError(
            f"Validation failed: {len(missing_codes)} AMFI codes found in fund_master "
            f"but missing from nav_history. See diagnostics above."
        )
    else:
        print()
        print("  AMFI CODE VALIDATION PASSED")
        print(f"All {len(fund_codes)} AMFI codes from fund_master are present in nav_history.")
        print(f"Total AMFI codes in nav_history: {len(nav_codes)}")
        print("=" * 70)
    
    return True


# ============================================================
# Transform
# ============================================================

def transform_dataset(name, df):
    """Clean and standardize a dataset."""
    
    config = DATASETS[name]
    
    # Store original column names for later validation
    original_columns = set(df.columns)
    
    # --------------------------------------------------------
    # Standardize column names
    # --------------------------------------------------------
    
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )
    
    # --------------------------------------------------------
    # Convert dates with explicit formats
    # --------------------------------------------------------
    
    date_formats = config.get("date_formats", {})
    date_month_columns = config.get("date_month_columns", [])
    
    for column in config["date_columns"]:
        
        if column in df.columns:
            
            # Check if this column is a month-level column (YYYY-MM format)
            is_month_column = column in date_month_columns
            
            # Use explicit format if defined
            if column in date_formats:
                format_str = date_formats[column]
                
                # Special handling for NAV dates
                if name == "nav_history" and column == "date":
                    # Validate dates before conversion to detect issues
                    
                    # First, check if dates are in expected format
                    # Try to parse with the explicit format
                    temp_dates = pd.to_datetime(
                        df[column],
                        format=format_str,
                        errors="coerce"
                    )
                    
                    invalid_mask = temp_dates.isna() & df[column].notna()
                    
                    if invalid_mask.any():
                        # Report detailed diagnostics
                        invalid_df = report_invalid_dates(
                            df[invalid_mask],
                            column,
                            name,
                            amfi_column="amfi_code" if "amfi_code" in df.columns else None,
                            nav_column="nav" if "nav" in df.columns else None
                        )
                        
                        raise ValueError(
                            f"{name}: {invalid_mask.sum()} invalid dates found in column '{column}'. "
                            f"Expected format: {format_str}. See diagnostics above for details."
                        )
                
                # Apply conversion with explicit format
                df[column] = pd.to_datetime(
                    df[column],
                    format=format_str,
                    errors="coerce"
                )
                
                # For month-level columns, ensure they are set to first day of month
                if is_month_column:
                    # Already parsed correctly, but ensure we have a valid datetime
                    # The format %Y-%m already gives us the first day of the month
                    pass
                
            else:
                # Fallback for dates without explicit format
                df[column] = pd.to_datetime(
                    df[column],
                    errors="coerce"
                )
            
            # Check for any NaT values after conversion
            invalid_dates = df[df[column].isna()]
            if len(invalid_dates) > 0 and column in date_formats:
                # Report diagnostics
                report_invalid_dates(
                    invalid_dates,
                    column,
                    name,
                    amfi_column="amfi_code" if "amfi_code" in df.columns else None
                )
                
                raise ValueError(
                    f"{name}: {len(invalid_dates)} invalid or missing dates in column '{column}'. "
                    f"Expected format: {date_formats.get(column, 'unknown')}"
                )
    
    # --------------------------------------------------------
    # Convert numeric columns
    # --------------------------------------------------------
    
    for column in config["numeric_columns"]:
        
        if column in df.columns:
            
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )
    
    # --------------------------------------------------------
    # Remove completely empty rows
    # --------------------------------------------------------
    
    df = df.dropna(how="all")
    
    # --------------------------------------------------------
    # Remove exact duplicate rows
    # --------------------------------------------------------
    
    df = df.drop_duplicates()
    
    # --------------------------------------------------------
    # NAV-specific processing
    # --------------------------------------------------------
    
    if name == "nav_history":
        
        # Validate AMFI codes are present and numeric
        invalid_amfi = df[df["amfi_code"].isna()]
        if len(invalid_amfi) > 0:
            print()
            print("=" * 70)
            print("INVALID AMFI CODES")
            print("=" * 70)
            print(f"Number of invalid/missing AMFI codes: {len(invalid_amfi)}")
            print()
            print("Sample records:")
            print(invalid_amfi.head(20).to_string(index=False))
            
            raise ValueError(
                f"nav_history: {len(invalid_amfi)} invalid or missing AMFI codes."
            )
        
        # Apply forward-fill (returns only amfi_code, date, nav)
        df = handle_nav_dates(df)
    
    # --------------------------------------------------------
    # Investor transactions specific validation
    # --------------------------------------------------------
    
    if name == "investor_transactions":
        df = validate_investor_transactions(df)
    
    # --------------------------------------------------------
    # Scheme performance specific validation
    # --------------------------------------------------------
    
    if name == "scheme_performance":
        df = validate_scheme_performance(df)
    
    # --------------------------------------------------------
    # Ensure we're not adding extra columns to NAV dataset
    # --------------------------------------------------------
    
    if name == "nav_history":
        # Verify only expected columns exist
        expected_cols = {"amfi_code", "date", "nav"}
        actual_cols = set(df.columns)
        
        if actual_cols != expected_cols:
            extra_cols = actual_cols - expected_cols
            missing_cols = expected_cols - actual_cols
            if extra_cols:
                raise ValueError(
                    f"nav_history: Unexpected columns found: {extra_cols}. "
                    f"Expected only: {expected_cols}"
                )
            if missing_cols:
                raise ValueError(
                    f"nav_history: Missing required columns: {missing_cols}"
                )
    
    return df


# ============================================================
# Validation
# ============================================================

def validate_dataset(name, df):
    """Validate required columns and basic data quality."""
    
    config = DATASETS[name]
    
    expected_columns = (
        config["date_columns"]
        + config["numeric_columns"]
    )
    
    missing_columns = [
        column
        for column in expected_columns
        if column not in df.columns
    ]
    
    if missing_columns:
        
        raise ValueError(
            f"{name}: missing columns: {missing_columns}"
        )
    
    # --------------------------------------------------------
    # Date validation - ensure no NaT values remain
    # --------------------------------------------------------
    
    for column in config["date_columns"]:
        
        invalid_dates = df[column].isna().sum()
        
        if invalid_dates > 0:
            
            # Get sample of invalid records
            invalid_df = df[df[column].isna()]
            
            print()
            print("=" * 70)
            print(f"INVALID DATES IN {name}.{column}")
            print("=" * 70)
            print(f"Number of invalid/missing dates: {invalid_dates}")
            print()
            print("Sample records:")
            print(invalid_df.head(20).to_string(index=False))
            
            raise ValueError(
                f"{name}: {invalid_dates} invalid or missing dates in column '{column}'. "
                "All dates must be valid and non-null."
            )
    
    # --------------------------------------------------------
    # AMFI code validation
    # --------------------------------------------------------
    
    if "amfi_code" in df.columns:
        
        missing_codes = df["amfi_code"].isna().sum()
        
        if missing_codes > 0:
            
            missing_df = df[df["amfi_code"].isna()]
            
            print()
            print("=" * 70)
            print(f"MISSING AMFI CODES IN {name}")
            print("=" * 70)
            print(f"Number of missing AMFI codes: {missing_codes}")
            print()
            print("Sample records:")
            print(missing_df.head(20).to_string(index=False))
            
            raise ValueError(
                f"{name}: {missing_codes} missing AMFI codes found."
            )
    
    # --------------------------------------------------------
    # NAV validation (should already be handled in transform)
    # --------------------------------------------------------
    
    if name == "nav_history":
        
        invalid_nav = (
            df["nav"].isna() |
            (df["nav"] <= 0)
        ).sum()
        
        if invalid_nav > 0:
            
            invalid_df = df[(df["nav"].isna()) | (df["nav"] <= 0)]
            
            print()
            print("=" * 70)
            print("INVALID NAV VALUES")
            print("=" * 70)
            print(f"Number of invalid NAV values: {invalid_nav}")
            print()
            print("Sample records:")
            print(invalid_df.head(20).to_string(index=False))
            
            raise ValueError(
                f"{name}: {invalid_nav} invalid NAV values found. "
                "NAV must be numeric and > 0."
            )
        
        duplicate_fund_dates = df.duplicated(
            subset=["amfi_code", "date"]
        ).sum()
        
        if duplicate_fund_dates > 0:
            
            dup_df = df[df.duplicated(subset=["amfi_code", "date"], keep=False)]
            
            print()
            print("=" * 70)
            print("DUPLICATE FUND/DATE COMBINATIONS")
            print("=" * 70)
            print(f"Number of duplicate rows: {duplicate_fund_dates}")
            print()
            print("Sample records:")
            print(dup_df.sort_values(["amfi_code", "date"]).head(20).to_string(index=False))
            
            raise ValueError(
                f"{name}: {duplicate_fund_dates} duplicate AMFI code + date rows found."
            )


# ============================================================
# Save cleaned dataset
# ============================================================

def save_dataset(name, df):
    """Save a cleaned dataset."""
    
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )
    
    output_path = (
        PROCESSED_DIR /
        f"{name}_cleaned.csv"
    )
    
    # For NAV dataset, ensure column order is amfi_code, date, nav
    if name == "nav_history":
        # Define the required column order
        required_cols = ["amfi_code", "date", "nav"]
        
        # Ensure all required columns exist
        missing_cols = [
            col for col in required_cols 
            if col not in df.columns
        ]
        
        if missing_cols:
            raise ValueError(
                f"nav_history: Missing columns before save: {missing_cols}"
            )
        
        # Keep only the required columns in the correct order
        df = df[required_cols]
        
        print(f"  Saving NAV with columns: {list(df.columns)}")
    
    # For all other datasets, preserve all columns
    else:
        print(f"  Saving {name} with columns: {list(df.columns)}")
    
    df.to_csv(
        output_path,
        index=False
    )


# ============================================================
# Load database
# ============================================================

def load_database():
    """Load cleaned datasets into SQLite."""
    
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )
    
    engine = create_engine(
        f"sqlite:///{DB_PATH}"
    )
    
    table_mapping = {
        
        "fund_master_cleaned.csv":
            "dim_fund",
        
        "nav_history_cleaned.csv":
            "fact_nav",
        
        "scheme_performance_cleaned.csv":
            "fact_performance",
        
        "investor_transactions_cleaned.csv":
            "fact_transactions",
        
        "portfolio_holdings_cleaned.csv":
            "fact_portfolio",
        
        "aum_by_fund_house_cleaned.csv":
            "fact_aum",
        
        "monthly_sip_inflows_cleaned.csv":
            "fact_sip_inflows",
        
        "benchmark_indices_cleaned.csv":
            "fact_benchmark",
        
        "category_inflows_cleaned.csv":
            "fact_category_inflows",
        
        "industry_folio_count_cleaned.csv":
            "fact_industry_folio_count"
    }
    
    for filename, table_name in table_mapping.items():
        
        path = PROCESSED_DIR / filename
        
        if not path.exists():
            
            raise FileNotFoundError(
                f"Processed dataset not found: {path}"
            )
        
        df = pd.read_csv(path)
        
        df.to_sql(
            table_name,
            engine,
            if_exists="replace",
            index=False
        )
        
        print(
            f"Loaded {table_name}"
        )


# ============================================================
# Main
# ============================================================

def main():
    """Run the complete ETL pipeline."""
    
    print()
    print("=" * 70)
    print("BLUESTOCK MUTUAL FUND ETL PIPELINE")
    print("=" * 70)
    
    successful_datasets = []
    failed_datasets = []
    
    for name in DATASETS:
        
        print()
        print("=" * 70)
        print(f"Processing: {name}")
        print("=" * 70)
        
        try:
            df = extract_dataset(name)
            
            original_rows = len(df)
            
            print(f"Original rows: {original_rows}")
            print(f"Original columns: {list(df.columns)}")
            
            df = transform_dataset(
                name,
                df
            )
            
            validate_dataset(
                name,
                df
            )
            
            save_dataset(
                name,
                df
            )
            
            print(f"Rows processed: {original_rows} -> {len(df)}")
            print(f"  {name} completed successfully")
            successful_datasets.append(name)
            
        except Exception as e:
            print()
            print("=" * 70)
            print(f"ERROR IN {name}")
            print("=" * 70)
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {e}")
            print()
            print("Pipeline stopped at this dataset.")
            failed_datasets.append(name)
            raise
    
    # Print summary of processed datasets
    print()
    print("=" * 70)
    print("DATASET PROCESSING SUMMARY")
    print("=" * 70)
    print(f"Successfully processed: {len(successful_datasets)} datasets")
    for ds in successful_datasets:
        print(f"  {ds} SUCCESS")
    if failed_datasets:
        print(f"Failed: {len(failed_datasets)} datasets")
        for ds in failed_datasets:
            print(f"  {ds} FAILED")
    print("=" * 70)
    
    # Cross-validation: AMFI codes in fund_master vs nav_history
    try:
        validate_amfi_codes()
    except Exception as e:
        print()
        print("=" * 70)
        print("AMFI CODE VALIDATION FAILED")
        print("=" * 70)
        print(f"Error: {e}")
        print()
        print("Pipeline stopped.")
        raise
    
    # Load all cleaned datasets into database
    print()
    print("=" * 70)
    print("LOADING DATABASE")
    print("=" * 70)
    
    load_database()
    
    print()
    print("=" * 70)
    print("ETL PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"Total datasets processed: {len(successful_datasets)} of {len(DATASETS)}")
    print("=" * 70)


# ============================================================
# Script entry point with pause on exit
# ============================================================

if __name__ == "__main__":
    exit_code = 0
    
    try:
        main()
    except Exception as e:
        print()
        print("=" * 70)
        print("FATAL ERROR")
        print("=" * 70)
        print(f"Error: {e}")
        exit_code = 1
    finally:
        # TEMPORARY DEBUGGING: Pause on exit if enabled
        if PAUSE_ON_EXIT:
            print()
            print("=" * 70)
            print("DEBUGGING PAUSE")
            print("=" * 70)
            print(f"PAUSE_ON_EXIT is {PAUSE_ON_EXIT}")
            print("Waiting 5 seconds before exiting...")
            print("(Set PAUSE_ON_EXIT = False to disable this pause)")
            print("=" * 70)
            time.sleep(5)
    
    sys.exit(exit_code)