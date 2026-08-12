"""
compute_metrics.py
Bluestock Mutual Fund Capstone

Day 4 - Fund Performance Analytics

Purpose:
Calculate key performance and risk metrics for mutual funds using
cleaned NAV history and benchmark data.

Inputs:
    data/processed/nav_history_cleaned.csv
    data/processed/fund_master_cleaned.csv
    data/processed/benchmark_indices_cleaned.csv
    data/processed/scheme_performance_cleaned.csv

Outputs:
    data/analytics/annualised_returns.csv
    data/analytics/cagr_report.csv
    data/analytics/standard_deviation.csv
    data/analytics/sharpe_values.csv
    data/analytics/sortino_values.csv
    data/analytics/alpha_beta.csv
    data/analytics/max_drawdown.csv
    data/analytics/comparison_table.csv
    data/analytics/fund_scorecard.csv
    data/analytics/tracking_error.csv
    data/analytics/category_performance.csv
    data/analytics/best_worst_by_category.csv

Main Day 4 objectives:
1. Compute key performance and risk metrics from NAV history
2. Build a fund ranking/scoring model
3. Compare fund returns against benchmark indices
4. Identify best and worst performing funds per category
"""

from pathlib import Path
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = BASE_DIR / "data" / "processed"
ANALYSIS_DIR = BASE_DIR / "data" / "analytics"

NAV_FILE = PROCESSED_DIR / "nav_history_cleaned.csv"
FUND_MASTER_FILE = PROCESSED_DIR / "fund_master_cleaned.csv"
BENCHMARK_FILE = PROCESSED_DIR / "benchmark_indices_cleaned.csv"
SCHEME_PERF_FILE = PROCESSED_DIR / "scheme_performance_cleaned.csv"


# ============================================================
# CONSTANTS
# ============================================================

TRADING_DAYS = 252
RISK_FREE_RATE = 0.0

SCORE_WEIGHTS = {
    "return_3yr_pct": 0.30,
    "sharpe_ratio": 0.25,
    "alpha": 0.20,
    "expense_ratio_pct": 0.15,
    "max_drawdown": 0.10,
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_minmax(series, higher_is_better=True):
    """
    Normalize a numeric series to 0-1.

    Higher values receive higher scores when
    higher_is_better=True.

    Lower values receive higher scores when
    higher_is_better=False.
    """

    series = pd.to_numeric(series, errors="coerce")

    min_value = series.min()
    max_value = series.max()

    if pd.isna(min_value) or pd.isna(max_value):
        return pd.Series(0.0, index=series.index)

    if max_value == min_value:
        return pd.Series(1.0, index=series.index)

    if higher_is_better:
        return (series - min_value) / (
            max_value - min_value
        )

    return (max_value - series) / (
        max_value - min_value
    )


def save_csv(df, filename):
    """
    Save dataframe to data/analytics.
    """

    ANALYSIS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = ANALYSIS_DIR / filename

    df.to_csv(
        output_path,
        index=False
    )

    print(f"Saved: {output_path}")

    return output_path


# ============================================================
# 1. LOAD DATA
# ============================================================

def load_data():
    """
    Load cleaned CSV files.

    Important:
    NAV history only needs:
        amfi_code, date, nav

    Fund metadata such as scheme_name, fund_house,
    category and plan comes from fund_master.
    """

    print("=" * 70)
    print("LOADING CLEANED DATA")
    print("=" * 70)

    required_files = [
        NAV_FILE,
        FUND_MASTER_FILE,
        BENCHMARK_FILE,
        SCHEME_PERF_FILE,
    ]

    for file_path in required_files:

        if not file_path.exists():

            raise FileNotFoundError(
                f"Required file not found:\n{file_path}"
            )

    nav_df = pd.read_csv(
        NAV_FILE
    )

    fund_master = pd.read_csv(
        FUND_MASTER_FILE
    )

    benchmark_df = pd.read_csv(
        BENCHMARK_FILE
    )

    scheme_perf = pd.read_csv(
        SCHEME_PERF_FILE
    )

    # --------------------------------------------------------
    # Validate required columns
    # --------------------------------------------------------

    required_nav_columns = {
        "amfi_code",
        "date",
        "nav",
    }

    required_fund_columns = {
        "amfi_code",
        "scheme_name",
        "fund_house",
        "category",
        "plan",
    }

    required_benchmark_columns = {
        "date",
        "index_name",
        "close_value",
    }

    required_scheme_perf_columns = {
        "amfi_code",
        "expense_ratio_pct",
        "aum_crore",
    }

    missing_nav = (
        required_nav_columns
        - set(nav_df.columns)
    )

    missing_fund = (
        required_fund_columns
        - set(fund_master.columns)
    )

    missing_benchmark = (
        required_benchmark_columns
        - set(benchmark_df.columns)
    )

    missing_scheme_perf = (
        required_scheme_perf_columns
        - set(scheme_perf.columns)
    )

    if missing_nav:
        raise ValueError(
            f"NAV file missing columns: "
            f"{sorted(missing_nav)}"
        )

    if missing_fund:
        raise ValueError(
            f"Fund master missing columns: "
            f"{sorted(missing_fund)}"
        )

    if missing_benchmark:
        raise ValueError(
            f"Benchmark file missing columns: "
            f"{sorted(missing_benchmark)}"
        )

    if missing_scheme_perf:
        raise ValueError(
            f"Scheme performance missing columns: "
            f"{sorted(missing_scheme_perf)}"
        )

    # --------------------------------------------------------
    # Convert dates
    # --------------------------------------------------------

    nav_df["date"] = pd.to_datetime(
        nav_df["date"],
        errors="coerce"
    )

    benchmark_df["date"] = pd.to_datetime(
        benchmark_df["date"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    nav_df["nav"] = pd.to_numeric(
        nav_df["nav"],
        errors="coerce"
    )

    benchmark_df["close_value"] = pd.to_numeric(
        benchmark_df["close_value"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Clean invalid records
    # --------------------------------------------------------

    nav_df = nav_df.dropna(
        subset=[
            "amfi_code",
            "date",
            "nav",
        ]
    ).copy()

    benchmark_df = benchmark_df.dropna(
        subset=[
            "date",
            "index_name",
            "close_value",
        ]
    ).copy()

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    nav_df = (
        nav_df
        .sort_values(
            ["amfi_code", "date"]
        )
        .reset_index(drop=True)
    )

    benchmark_df = (
        benchmark_df
        .sort_values(
            ["index_name", "date"]
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Create fund metadata lookup
    #
    # NAV does not contain scheme_name.
    # Merge the metadata onto NAV here once.
    # --------------------------------------------------------

    fund_metadata = (
        fund_master[
            [
                "amfi_code",
                "scheme_name",
                "fund_house",
                "category",
                "sub_category",
                "plan",
            ]
        ]
        .drop_duplicates("amfi_code")
        .copy()
    )

    nav_df = nav_df.merge(
        fund_metadata,
        on="amfi_code",
        how="left"
    )

    # --------------------------------------------------------
    # Validation after metadata merge
    # --------------------------------------------------------

    missing_names = nav_df[
        "scheme_name"
    ].isna().sum()

    if missing_names > 0:

        print(
            f"WARNING: {missing_names:,} NAV records "
            f"could not be matched to fund master."
        )

    # --------------------------------------------------------
    # Information
    # --------------------------------------------------------

    print(
        f"NAV records: "
        f"{len(nav_df):,}"
    )

    print(
        f"Schemes in NAV data: "
        f"{nav_df['amfi_code'].nunique()}"
    )

    print(
        f"Fund master schemes: "
        f"{fund_master['amfi_code'].nunique()}"
    )

    print(
        f"Benchmark records: "
        f"{len(benchmark_df):,}"
    )

    print(
        f"NAV date range: "
        f"{nav_df['date'].min().date()} "
        f"to "
        f"{nav_df['date'].max().date()}"
    )

    print(
        f"Analysis output directory: "
        f"{ANALYSIS_DIR}"
    )

    return (
        nav_df,
        fund_master,
        benchmark_df,
        scheme_perf,
    )


# ============================================================
# 2. DAILY RETURNS
# ============================================================

def calculate_daily_returns(nav_df):
    """
    Calculate daily percentage returns for every fund.
    """

    print("\n" + "=" * 70)
    print("CALCULATING DAILY RETURNS")
    print("=" * 70)

    nav_df = nav_df.copy()

    nav_df = (
        nav_df
        .sort_values(
            ["amfi_code", "date"]
        )
        .reset_index(drop=True)
    )

    nav_df["daily_return"] = (
        nav_df
        .groupby("amfi_code")["nav"]
        .pct_change()
    )

    returns_df = nav_df.dropna(
        subset=["daily_return"]
    ).copy()

    total_obs = len(
        returns_df
    )

    fund_count = (
        returns_df["amfi_code"]
        .nunique()
    )

    mean_return = (
        returns_df["daily_return"]
        .mean()
    )

    std_return = (
        returns_df["daily_return"]
        .std()
    )

    min_return = (
        returns_df["daily_return"]
        .min()
    )

    max_return = (
        returns_df["daily_return"]
        .max()
    )

    extreme = returns_df[
        returns_df["daily_return"].abs() > 0.20
    ]

    print(
        f"Daily returns computed for "
        f"{fund_count} schemes"
    )

    print(
        f"Total return observations: "
        f"{total_obs:,}"
    )

    print(
        f"Mean daily return: "
        f"{mean_return:.6f}"
    )

    print(
        f"Std dev: "
        f"{std_return:.6f}"
    )

    print(
        f"Minimum: "
        f"{min_return:.6f}"
    )

    print(
        f"Maximum: "
        f"{max_return:.6f}"
    )

    if total_obs > 0:

        print(
            f"Extreme returns (>20% or <-20%): "
            f"{len(extreme)} "
            f"({len(extreme) / total_obs * 100:.2f}%)"
        )

    return nav_df, returns_df


# ============================================================
# 3. ANNUALISED RETURN
# ============================================================

def calculate_annualised_returns(returns_df):
    """
    Calculate annualised compounded return from
    average daily return.

    Formula:
        (1 + mean_daily_return)^252 - 1
    """

    print("\n" + "=" * 70)
    print("CALCULATING ANNUALISED RETURNS")
    print("=" * 70)

    fund_returns = (
        returns_df
        .groupby("amfi_code")["daily_return"]
        .mean()
    )

    annualised = (
        (1 + fund_returns)
        ** TRADING_DAYS
    ) - 1

    annualised_df = (
        annualised
        .reset_index()
    )

    annualised_df.columns = [
        "amfi_code",
        "annualised_return",
    ]

    # Scheme name already exists in NAV after
    # the metadata merge in load_data().
    scheme_names = (
        returns_df[
            [
                "amfi_code",
                "scheme_name",
            ]
        ]
        .drop_duplicates("amfi_code")
    )

    annualised_df = annualised_df.merge(
        scheme_names,
        on="amfi_code",
        how="left"
    )

    annualised_df[
        "annualised_return"
    ] = (
        annualised_df[
            "annualised_return"
        ].round(6)
    )

    print(
        f"Mean annualised return: "
        f"{annualised_df['annualised_return'].mean():.4f}"
    )

    print(
        f"Median annualised return: "
        f"{annualised_df['annualised_return'].median():.4f}"
    )

    print(
        f"Maximum: "
        f"{annualised_df['annualised_return'].max():.4f}"
    )

    print(
        f"Minimum: "
        f"{annualised_df['annualised_return'].min():.4f}"
    )

    save_csv(
        annualised_df,
        "annualised_returns.csv"
    )

    return annualised_df


# ============================================================
# 4. CAGR
# ============================================================

def calculate_cagr(nav_df):
    """
    Calculate 1-year, 3-year and 5-year CAGR.

    For each fund:
        - Take its latest available NAV.
        - Find NAV on or before target historical date.
        - Calculate CAGR using actual elapsed time.
    """

    print("\n" + "=" * 70)
    print("CALCULATING CAGR")
    print("=" * 70)

    results = []

    periods = {
        "1yr": 365,
        "3yr": 3 * 365,
        "5yr": 5 * 365,
    }

    for fund_code, fund_data in (
        nav_df.groupby("amfi_code")
    ):

        fund_data = (
            fund_data
            .sort_values("date")
            .copy()
        )

        if len(fund_data) < 2:
            continue

        latest_row = (
            fund_data.iloc[-1]
        )

        latest_nav = latest_row["nav"]
        latest_date = latest_row["date"]
        scheme_name = latest_row[
            "scheme_name"
        ]

        result = {
            "amfi_code": fund_code,
            "scheme_name": scheme_name,
        }

        for period_name, days in periods.items():

            target_date = (
                latest_date
                - pd.Timedelta(
                    days=days
                )
            )

            historical = fund_data[
                fund_data["date"]
                <= target_date
            ]

            if historical.empty:

                result[
                    f"cagr_{period_name}"
                ] = np.nan

                continue

            historical_row = (
                historical.iloc[-1]
            )

            past_nav = historical_row[
                "nav"
            ]

            past_date = historical_row[
                "date"
            ]

            if (
                past_nav <= 0
                or latest_nav <= 0
            ):

                result[
                    f"cagr_{period_name}"
                ] = np.nan

                continue

            elapsed_days = (
                latest_date
                - past_date
            ).days

            if elapsed_days <= 0:

                result[
                    f"cagr_{period_name}"
                ] = np.nan

                continue

            years = (
                elapsed_days / 365.25
            )

            cagr = (
                (latest_nav / past_nav)
                ** (1 / years)
            ) - 1

            result[
                f"cagr_{period_name}"
            ] = round(
                cagr,
                6
            )

        results.append(result)

    cagr_df = pd.DataFrame(
        results
    )

    for period in [
        "1yr",
        "3yr",
        "5yr",
    ]:

        column = f"cagr_{period}"

        print(
            f"{period} CAGR - "
            f"Mean: {cagr_df[column].mean():.4f}, "
            f"Median: {cagr_df[column].median():.4f}"
        )

    print(
        "\nTop 3 schemes by 3-Year CAGR:"
    )

    top_3 = (
        cagr_df
        .nlargest(
            3,
            "cagr_3yr"
        )
        [
            [
                "scheme_name",
                "cagr_3yr",
            ]
        ]
    )

    print(
        top_3.to_string(
            index=False
        )
    )

    save_csv(
        cagr_df,
        "cagr_report.csv"
    )

    return cagr_df


# ============================================================
# 5. STANDARD DEVIATION
# ============================================================

def calculate_standard_deviation(
    returns_df
):
    """
    Calculate annualised standard deviation.
    """

    print("\n" + "=" * 70)
    print(
        "CALCULATING ANNUALISED STANDARD DEVIATION"
    )
    print("=" * 70)

    daily_std = (
        returns_df
        .groupby("amfi_code")[
            "daily_return"
        ]
        .std()
    )

    annual_std = (
        daily_std
        * np.sqrt(TRADING_DAYS)
    )

    std_df = (
        annual_std
        .reset_index()
    )

    std_df.columns = [
        "amfi_code",
        "std_dev_ann_pct",
    ]

    # Convert decimal to percentage.
    std_df[
        "std_dev_ann_pct"
    ] *= 100

    scheme_names = (
        returns_df[
            [
                "amfi_code",
                "scheme_name",
            ]
        ]
        .drop_duplicates(
            "amfi_code"
        )
    )

    std_df = std_df.merge(
        scheme_names,
        on="amfi_code",
        how="left"
    )

    std_df[
        "std_dev_ann_pct"
    ] = (
        std_df[
            "std_dev_ann_pct"
        ].round(4)
    )

    save_csv(
        std_df,
        "standard_deviation.csv"
    )

    return std_df


# ============================================================
# 6. SHARPE RATIO
# ============================================================

def calculate_sharpe_ratio(
    returns_df,
    std_df,
):
    """
    Calculate Sharpe ratio.

    Risk-free rate = 0%.

    Sharpe =
        (annualised return - risk free rate)
        / annualised volatility
    """

    print("\n" + "=" * 70)
    print("CALCULATING SHARPE RATIOS")
    print("=" * 70)

    mean_daily = (
        returns_df
        .groupby("amfi_code")[
            "daily_return"
        ]
        .mean()
    )

    annual_return = (
        (1 + mean_daily)
        ** TRADING_DAYS
    ) - 1

    sharpe_df = (
        annual_return
        .reset_index()
    )

    sharpe_df.columns = [
        "amfi_code",
        "annual_return",
    ]

    sharpe_df = sharpe_df.merge(
        std_df[
            [
                "amfi_code",
                "std_dev_ann_pct",
            ]
        ],
        on="amfi_code",
        how="left"
    )

    annual_std_decimal = (
        sharpe_df[
            "std_dev_ann_pct"
        ] / 100
    )

    sharpe_df[
        "sharpe_ratio"
    ] = (
        (
            sharpe_df[
                "annual_return"
            ]
            - RISK_FREE_RATE
        )
        / annual_std_decimal
    )

    scheme_names = (
        returns_df[
            [
                "amfi_code",
                "scheme_name",
            ]
        ]
        .drop_duplicates(
            "amfi_code"
        )
    )

    sharpe_df = sharpe_df.merge(
        scheme_names,
        on="amfi_code",
        how="left"
    )

    sharpe_df[
        "sharpe_ratio"
    ] = (
        sharpe_df[
            "sharpe_ratio"
        ]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .round(4)
    )

    print(
        f"Mean Sharpe ratio: "
        f"{sharpe_df['sharpe_ratio'].mean():.4f}"
    )

    print(
        f"Median Sharpe ratio: "
        f"{sharpe_df['sharpe_ratio'].median():.4f}"
    )

    print(
        f"Maximum Sharpe ratio: "
        f"{sharpe_df['sharpe_ratio'].max():.4f}"
    )

    print(
        f"Minimum Sharpe ratio: "
        f"{sharpe_df['sharpe_ratio'].min():.4f}"
    )

    print(
        "\nTop 5 schemes by Sharpe ratio:"
    )

    print(
        sharpe_df
        .nlargest(
            5,
            "sharpe_ratio"
        )
        [
            [
                "scheme_name",
                "sharpe_ratio",
            ]
        ]
        .to_string(index=False)
    )

    output = sharpe_df[
        [
            "amfi_code",
            "scheme_name",
            "sharpe_ratio",
        ]
    ].copy()

    save_csv(
        output,
        "sharpe_values.csv"
    )

    return sharpe_df


# ============================================================
# 7. SORTINO RATIO
# ============================================================

def calculate_sortino_ratio(
    returns_df
):
    """
    Calculate Sortino ratio using downside deviation.

    Risk-free rate = 0%.
    """

    print("\n" + "=" * 70)
    print("CALCULATING SORTINO RATIOS")
    print("=" * 70)

    mean_daily = (
        returns_df
        .groupby("amfi_code")[
            "daily_return"
        ]
        .mean()
    )

    annual_return = (
        (1 + mean_daily)
        ** TRADING_DAYS
    ) - 1

    downside_std = (
        returns_df[
            returns_df["daily_return"] < 0
        ]
        .groupby("amfi_code")[
            "daily_return"
        ]
        .std()
    )

    downside_std_ann = (
        downside_std
        * np.sqrt(TRADING_DAYS)
    )

    sortino_df = (
        annual_return
        .reset_index()
    )

    sortino_df.columns = [
        "amfi_code",
        "annual_return",
    ]

    sortino_df = sortino_df.merge(
        downside_std_ann.reset_index(
            name="downside_std_ann"
        ),
        on="amfi_code",
        how="left"
    )

    sortino_df[
        "sortino_ratio"
    ] = (
        sortino_df[
            "annual_return"
        ]
        / sortino_df[
            "downside_std_ann"
        ]
    )

    scheme_names = (
        returns_df[
            [
                "amfi_code",
                "scheme_name",
            ]
        ]
        .drop_duplicates(
            "amfi_code"
        )
    )

    sortino_df = sortino_df.merge(
        scheme_names,
        on="amfi_code",
        how="left"
    )

    sortino_df[
        "sortino_ratio"
    ] = (
        sortino_df[
            "sortino_ratio"
        ]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .round(4)
    )

    print(
        f"Mean Sortino ratio: "
        f"{sortino_df['sortino_ratio'].mean():.4f}"
    )

    print(
        f"Median Sortino ratio: "
        f"{sortino_df['sortino_ratio'].median():.4f}"
    )

    print(
        f"Maximum Sortino ratio: "
        f"{sortino_df['sortino_ratio'].max():.4f}"
    )

    print(
        f"Minimum Sortino ratio: "
        f"{sortino_df['sortino_ratio'].min():.4f}"
    )

    print(
        "\nTop 5 schemes by Sortino ratio:"
    )

    print(
        sortino_df
        .nlargest(
            5,
            "sortino_ratio"
        )
        [
            [
                "scheme_name",
                "sortino_ratio",
            ]
        ]
        .to_string(index=False)
    )

    output = sortino_df[
        [
            "amfi_code",
            "scheme_name",
            "sortino_ratio",
        ]
    ].copy()

    save_csv(
        output,
        "sortino_values.csv"
    )

    return sortino_df


# ============================================================
# 8. ALPHA AND BETA
# ============================================================

def calculate_alpha_beta(
    returns_df,
    benchmark_df,
):
    """
    Calculate Alpha, Beta and R-squared against NIFTY100.

    Regression:

        Fund Return =
            Alpha + Beta * NIFTY100 Return

    Alpha is annualised.
    """

    print("\n" + "=" * 70)
    print("CALCULATING ALPHA AND BETA")
    print("=" * 70)

    nifty100 = benchmark_df[
        benchmark_df["index_name"]
        == "NIFTY100"
    ].copy()

    if nifty100.empty:

        print(
            "WARNING: NIFTY100 benchmark "
            "data not found."
        )

        return pd.DataFrame(
            columns=[
                "amfi_code",
                "scheme_name",
                "alpha",
                "beta",
                "r_squared",
                "observations",
            ]
        )

    nifty100 = (
        nifty100
        .sort_values("date")
        .copy()
    )

    nifty100[
        "benchmark_return"
    ] = (
        nifty100[
            "close_value"
        ].pct_change()
    )

    nifty100 = nifty100.dropna(
        subset=[
            "benchmark_return"
        ]
    )

    fund_returns = returns_df[
        [
            "amfi_code",
            "scheme_name",
            "date",
            "daily_return",
        ]
    ].copy()

    merged = fund_returns.merge(
        nifty100[
            [
                "date",
                "benchmark_return",
            ]
        ],
        on="date",
        how="inner"
    )

    results = []

    for fund_code, fund_data in (
        merged.groupby("amfi_code")
    ):

        if len(fund_data) < 30:
            continue

        x = (
            fund_data[
                "benchmark_return"
            ].values
        )

        y = (
            fund_data[
                "daily_return"
            ].values
        )

        benchmark_variance = np.var(
            x,
            ddof=1
        )

        if benchmark_variance == 0:
            continue

        covariance = np.cov(
            x,
            y,
            ddof=1
        )[0, 1]

        beta = (
            covariance
            / benchmark_variance
        )

        alpha_daily = (
            y.mean()
            - beta * x.mean()
        )

        alpha_annual = (
            (1 + alpha_daily)
            ** TRADING_DAYS
        ) - 1

        y_pred = (
            alpha_daily
            + beta * x
        )

        ss_res = np.sum(
            (y - y_pred) ** 2
        )

        ss_tot = np.sum(
            (y - y.mean()) ** 2
        )

        r_squared = (
            1 - ss_res / ss_tot
            if ss_tot != 0
            else np.nan
        )

        results.append(
            {
                "amfi_code": fund_code,
                "scheme_name": (
                    fund_data[
                        "scheme_name"
                    ].iloc[0]
                ),
                "alpha": round(
                    alpha_annual * 100,
                    4
                ),
                "beta": round(
                    beta,
                    4
                ),
                "r_squared": round(
                    r_squared,
                    6
                ),
                "observations": len(
                    fund_data
                ),
            }
        )

    alpha_beta_df = pd.DataFrame(
        results
    )

    print(
        f"Funds analysed: "
        f"{len(alpha_beta_df)}"
    )

    if not alpha_beta_df.empty:

        print(
            f"Alpha range: "
            f"{alpha_beta_df['alpha'].min():.4f} "
            f"to "
            f"{alpha_beta_df['alpha'].max():.4f}"
        )

        print(
            f"Beta range: "
            f"{alpha_beta_df['beta'].min():.4f} "
            f"to "
            f"{alpha_beta_df['beta'].max():.4f}"
        )

        print(
            f"Mean R-squared: "
            f"{alpha_beta_df['r_squared'].mean():.6f}"
        )

    save_csv(
        alpha_beta_df,
        "alpha_beta.csv"
    )

    return alpha_beta_df


# ============================================================
# 9. MAXIMUM DRAWDOWN
# ============================================================

def calculate_max_drawdown(
    nav_df
):
    """
    Calculate maximum drawdown for each fund.

    Also records:
        peak_date
        trough_date
    """

    print("\n" + "=" * 70)
    print("CALCULATING MAXIMUM DRAWDOWN")
    print("=" * 70)

    results = []

    for fund_code, fund_data in (
        nav_df.groupby("amfi_code")
    ):

        fund_data = (
            fund_data
            .sort_values("date")
            .copy()
        )

        if len(fund_data) < 2:
            continue

        nav_values = (
            fund_data[
                "nav"
            ].to_numpy()
        )

        dates = (
            fund_data[
                "date"
            ].to_numpy()
        )

        running_max = (
            np.maximum.accumulate(
                nav_values
            )
        )

        drawdowns = (
            nav_values
            / running_max
        ) - 1

        trough_idx = int(
            np.argmin(drawdowns)
        )

        max_drawdown = (
            drawdowns[trough_idx]
        )

        peak_idx = int(
            np.argmax(
                nav_values[
                    :trough_idx + 1
                ]
            )
        )

        results.append(
            {
                "amfi_code": fund_code,
                "scheme_name": (
                    fund_data[
                        "scheme_name"
                    ].iloc[0]
                ),
                "max_drawdown": round(
                    max_drawdown * 100,
                    4
                ),
                "peak_date": pd.Timestamp(
                    dates[peak_idx]
                ).strftime(
                    "%Y-%m-%d"
                ),
                "trough_date": pd.Timestamp(
                    dates[trough_idx]
                ).strftime(
                    "%Y-%m-%d"
                ),
            }
        )

    max_dd_df = pd.DataFrame(
        results
    )

    print(
        f"Mean max drawdown: "
        f"{max_dd_df['max_drawdown'].mean():.2f}%"
    )

    print(
        f"Deepest max drawdown: "
        f"{max_dd_df['max_drawdown'].min():.2f}%"
    )

    print(
        f"Smallest max drawdown: "
        f"{max_dd_df['max_drawdown'].max():.2f}%"
    )

    save_csv(
        max_dd_df,
        "max_drawdown.csv"
    )

    return max_dd_df


# ============================================================
# 10. COMPARISON TABLE
# ============================================================

def build_comparison_table(
    fund_master,
    scheme_perf,
    cagr_df,
    std_df,
    sharpe_df,
    sortino_df,
    alpha_beta_df,
    max_dd_df,
):
    """
    Build one comprehensive fund comparison table.
    """

    print("\n" + "=" * 70)
    print("BUILDING FUND COMPARISON TABLE")
    print("=" * 70)

    # --------------------------------------------------------
    # Base fund information
    # --------------------------------------------------------

    comparison = (
        fund_master[
            [
                "amfi_code",
                "scheme_name",
                "fund_house",
                "category",
                "sub_category",
                "plan",
            ]
        ]
        .drop_duplicates("amfi_code")
        .copy()
    )

    # --------------------------------------------------------
    # CAGR
    # --------------------------------------------------------

    comparison = comparison.merge(
        cagr_df[
            [
                "amfi_code",
                "cagr_1yr",
                "cagr_3yr",
                "cagr_5yr",
            ]
        ],
        on="amfi_code",
        how="left"
    )

    comparison.rename(
        columns={
            "cagr_1yr": "return_1yr_pct",
            "cagr_3yr": "return_3yr_pct",
            "cagr_5yr": "return_5yr_pct",
        },
        inplace=True
    )

    # CAGR values are decimals.
    # Convert to percentage.
    for column in [
        "return_1yr_pct",
        "return_3yr_pct",
        "return_5yr_pct",
    ]:

        comparison[column] *= 100

    # --------------------------------------------------------
    # Sharpe
    # --------------------------------------------------------

    comparison = comparison.merge(
        sharpe_df[
            [
                "amfi_code",
                "sharpe_ratio",
            ]
        ],
        on="amfi_code",
        how="left"
    )

    # --------------------------------------------------------
    # Sortino
    # --------------------------------------------------------

    comparison = comparison.merge(
        sortino_df[
            [
                "amfi_code",
                "sortino_ratio",
            ]
        ],
        on="amfi_code",
        how="left"
    )

    # --------------------------------------------------------
    # Alpha / Beta
    # --------------------------------------------------------

    comparison = comparison.merge(
        alpha_beta_df[
            [
                "amfi_code",
                "alpha",
                "beta",
                "r_squared",
            ]
        ],
        on="amfi_code",
        how="left"
    )

    # --------------------------------------------------------
    # Standard deviation
    # --------------------------------------------------------

    comparison = comparison.merge(
        std_df[
            [
                "amfi_code",
                "std_dev_ann_pct",
            ]
        ],
        on="amfi_code",
        how="left"
    )

    # --------------------------------------------------------
    # Maximum drawdown
    # --------------------------------------------------------

    comparison = comparison.merge(
        max_dd_df[
            [
                "amfi_code",
                "max_drawdown",
                "peak_date",
                "trough_date",
            ]
        ],
        on="amfi_code",
        how="left"
    )

    # --------------------------------------------------------
    # Expense ratio and AUM
    # --------------------------------------------------------

    performance_columns = [
        "amfi_code",
        "expense_ratio_pct",
        "aum_crore",
    ]

    performance_info = (
        scheme_perf[
            performance_columns
        ]
        .drop_duplicates(
            "amfi_code"
        )
    )

    comparison = comparison.merge(
        performance_info,
        on="amfi_code",
        how="left"
    )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    comparison = (
        comparison
        .sort_values(
            "return_3yr_pct",
            ascending=False
        )
        .reset_index(drop=True)
    )

    numeric_columns = (
        comparison
        .select_dtypes(
            include=np.number
        )
        .columns
    )

    comparison[
        numeric_columns
    ] = (
        comparison[
            numeric_columns
        ].round(4)
    )

    save_csv(
        comparison,
        "comparison_table.csv"
    )

    print(
        "\nTop 10 funds by 3-year return:"
    )

    display_columns = [
        "scheme_name",
        "category",
        "return_3yr_pct",
        "sharpe_ratio",
        "std_dev_ann_pct",
    ]

    print(
        comparison[
            display_columns
        ]
        .head(10)
        .to_string(index=False)
    )

    return comparison


# ============================================================
# 11. FUND SCORECARD
# ============================================================

def calculate_fund_scorecard(
    comparison_df
):
    """
    Create a 0-100 composite fund score.

    Weights:
        3Y Return       30%
        Sharpe          25%
        Alpha           20%
        Expense Ratio   15%
        Max Drawdown    10%
    """

    print("\n" + "=" * 70)
    print("BUILDING FUND SCORECARD")
    print("=" * 70)

    scorecard = comparison_df.copy()

    # --------------------------------------------------------
    # Normalize metrics
    # --------------------------------------------------------

    scorecard[
        "return_score"
    ] = safe_minmax(
        scorecard[
            "return_3yr_pct"
        ],
        higher_is_better=True
    )

    scorecard[
        "sharpe_score"
    ] = safe_minmax(
        scorecard[
            "sharpe_ratio"
        ],
        higher_is_better=True
    )

    scorecard[
        "alpha_score"
    ] = safe_minmax(
        scorecard[
            "alpha"
        ],
        higher_is_better=True
    )

    scorecard[
        "expense_score"
    ] = safe_minmax(
        scorecard[
            "expense_ratio_pct"
        ],
        higher_is_better=False
    )

    scorecard[
        "drawdown_score"
    ] = safe_minmax(
        scorecard[
            "max_drawdown"
        ],
        higher_is_better=True
    )

    score_columns = [
        "return_score",
        "sharpe_score",
        "alpha_score",
        "expense_score",
        "drawdown_score",
    ]

    scorecard[
        score_columns
    ] = (
        scorecard[
            score_columns
        ].fillna(0)
    )

    # --------------------------------------------------------
    # Weighted score
    # --------------------------------------------------------

    scorecard["score"] = (

        SCORE_WEIGHTS[
            "return_3yr_pct"
        ]
        * scorecard[
            "return_score"
        ]

        +

        SCORE_WEIGHTS[
            "sharpe_ratio"
        ]
        * scorecard[
            "sharpe_score"
        ]

        +

        SCORE_WEIGHTS[
            "alpha"
        ]
        * scorecard[
            "alpha_score"
        ]

        +

        SCORE_WEIGHTS[
            "expense_ratio_pct"
        ]
        * scorecard[
            "expense_score"
        ]

        +

        SCORE_WEIGHTS[
            "max_drawdown"
        ]
        * scorecard[
            "drawdown_score"
        ]

    ) * 100

    scorecard["score"] = (
        scorecard["score"]
        .round(2)
    )

    scorecard = (
        scorecard
        .sort_values(
            "score",
            ascending=False
        )
        .reset_index(drop=True)
    )

    output_columns = [
        "amfi_code",
        "scheme_name",
        "fund_house",
        "category",
        "plan",
        "score",
        "return_3yr_pct",
        "sharpe_ratio",
        "alpha",
        "expense_ratio_pct",
        "max_drawdown",
    ]

    scorecard_output = (
        scorecard[
            output_columns
        ].copy()
    )

    print(
        f"Highest score: "
        f"{scorecard_output['score'].max():.2f}"
    )

    print(
        f"Lowest score: "
        f"{scorecard_output['score'].min():.2f}"
    )

    print(
        f"Mean score: "
        f"{scorecard_output['score'].mean():.2f}"
    )

    print(
        "\nTop 10 funds by score:"
    )

    print(
        scorecard_output[
            [
                "scheme_name",
                "category",
                "score",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    save_csv(
        scorecard_output,
        "fund_scorecard.csv"
    )

    return scorecard_output


# ============================================================
# 12. TRACKING ERROR
# ============================================================

def calculate_tracking_error(
    returns_df,
    benchmark_df,
    cagr_df,
):
    """
    Calculate annualised tracking error for the top 5
    funds by 3-year CAGR against NIFTY50 and NIFTY100.

    Tracking Error =
        Std Dev(Fund Return - Benchmark Return)
        * sqrt(252)
    """

    print("\n" + "=" * 70)
    print("CALCULATING TRACKING ERROR")
    print("=" * 70)

    top_5_codes = (
        cagr_df
        .nlargest(
            5,
            "cagr_3yr"
        )
        ["amfi_code"]
        .tolist()
    )

    results = []

    for benchmark_name in [
        "NIFTY50",
        "NIFTY100",
    ]:

        benchmark = benchmark_df[
            benchmark_df[
                "index_name"
            ] == benchmark_name
        ].copy()

        if benchmark.empty:

            print(
                f"WARNING: {benchmark_name} "
                f"benchmark not found."
            )

            continue

        benchmark = (
            benchmark
            .sort_values("date")
            .copy()
        )

        benchmark[
            "benchmark_return"
        ] = (
            benchmark[
                "close_value"
            ].pct_change()
        )

        benchmark = benchmark.dropna(
            subset=[
                "benchmark_return"
            ]
        )

        for fund_code in top_5_codes:

            fund = returns_df[
                returns_df[
                    "amfi_code"
                ] == fund_code
            ].copy()

            merged = fund[
                [
                    "amfi_code",
                    "scheme_name",
                    "date",
                    "daily_return",
                ]
            ].merge(
                benchmark[
                    [
                        "date",
                        "benchmark_return",
                    ]
                ],
                on="date",
                how="inner"
            )

            if len(merged) < 30:
                continue

            excess_return = (
                merged[
                    "daily_return"
                ]
                - merged[
                    "benchmark_return"
                ]
            )

            tracking_error = (
                excess_return.std()
                * np.sqrt(TRADING_DAYS)
            )

            results.append(
                {
                    "amfi_code": fund_code,
                    "scheme_name": (
                        merged[
                            "scheme_name"
                        ].iloc[0]
                    ),
                    "benchmark": benchmark_name,
                    "tracking_error": round(
                        tracking_error,
                        6
                    ),
                }
            )

    tracking_error_df = pd.DataFrame(
        results
    )

    if not tracking_error_df.empty:

        print(
            "\nTracking Error results:"
        )

        print(
            tracking_error_df
            .to_string(index=False)
        )

        print(
            "\nMean tracking error: "
            f"{tracking_error_df['tracking_error'].mean():.4f}"
        )

    else:

        print(
            "No tracking error data available."
        )

    save_csv(
        tracking_error_df,
        "tracking_error.csv"
    )

    return tracking_error_df


# ============================================================
# 13. BEST / WORST BY CATEGORY
# ============================================================

def calculate_best_worst_by_category(
    comparison_df
):
    """
    Identify best and worst funds within each category
    based on 3-year return.
    """

    print("\n" + "=" * 70)
    print("BEST / WORST FUND BY CATEGORY")
    print("=" * 70)

    results = []

    for category, category_df in (
        comparison_df
        .groupby("category")
    ):

        category_df = category_df.dropna(
            subset=[
                "return_3yr_pct"
            ]
        ).copy()

        if category_df.empty:
            continue

        best = category_df.loc[
            category_df[
                "return_3yr_pct"
            ].idxmax()
        ]

        worst = category_df.loc[
            category_df[
                "return_3yr_pct"
            ].idxmin()
        ]

        results.append(
            {
                "category": category,

                "best_fund": best[
                    "scheme_name"
                ],

                "best_return_3yr_pct": best[
                    "return_3yr_pct"
                ],

                "best_sharpe": best[
                    "sharpe_ratio"
                ],

                "best_alpha": best[
                    "alpha"
                ],

                "best_std_dev_pct": best[
                    "std_dev_ann_pct"
                ],

                "worst_fund": worst[
                    "scheme_name"
                ],

                "worst_return_3yr_pct": worst[
                    "return_3yr_pct"
                ],

                "worst_sharpe": worst[
                    "sharpe_ratio"
                ],

                "worst_alpha": worst[
                    "alpha"
                ],

                "worst_std_dev_pct": worst[
                    "std_dev_ann_pct"
                ],

                "return_spread_pct": (
                    best[
                        "return_3yr_pct"
                    ]
                    - worst[
                        "return_3yr_pct"
                    ]
                ),
            }
        )

    result_df = pd.DataFrame(
        results
    )

    if not result_df.empty:

        result_df = (
            result_df
            .sort_values("category")
            .reset_index(drop=True)
        )

        print(
            result_df[
                [
                    "category",
                    "best_fund",
                    "best_return_3yr_pct",
                    "worst_fund",
                    "worst_return_3yr_pct",
                    "return_spread_pct",
                ]
            ]
            .to_string(index=False)
        )

    save_csv(
        result_df,
        "best_worst_by_category.csv"
    )

    return result_df


# ============================================================
# 14. CATEGORY PERFORMANCE SUMMARY
# ============================================================

def calculate_category_performance(
    comparison_df
):
    """
    Aggregate 3-year return, Sharpe ratio and
    volatility by fund category.
    """

    print("\n" + "=" * 70)
    print("CATEGORY PERFORMANCE SUMMARY")
    print("=" * 70)

    category_df = (
        comparison_df
        .groupby("category")
        .agg(
            schemes=(
                "amfi_code",
                "nunique",
            ),

            mean_return_3yr_pct=(
                "return_3yr_pct",
                "mean",
            ),

            max_return_3yr_pct=(
                "return_3yr_pct",
                "max",
            ),

            min_return_3yr_pct=(
                "return_3yr_pct",
                "min",
            ),

            mean_sharpe=(
                "sharpe_ratio",
                "mean",
            ),

            mean_std_dev_pct=(
                "std_dev_ann_pct",
                "mean",
            ),
        )
        .reset_index()
    )

    category_df = (
        category_df
        .round(4)
    )

    print(
        category_df.to_string(
            index=False
        )
    )

    save_csv(
        category_df,
        "category_performance.csv"
    )

    return category_df


# ============================================================
# 15. MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 70)
    print(
        "BLUESTOCK MUTUAL FUND "
        "PERFORMANCE ANALYTICS"
    )
    print("DAY 4")
    print("=" * 70)

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    (
        nav_df,
        fund_master,
        benchmark_df,
        scheme_perf,
    ) = load_data()

    # --------------------------------------------------------
    # Daily returns
    # --------------------------------------------------------

    nav_with_returns, returns_df = (
        calculate_daily_returns(
            nav_df
        )
    )

    # --------------------------------------------------------
    # Performance metrics
    # --------------------------------------------------------

    annualised_df = (
        calculate_annualised_returns(
            returns_df
        )
    )

    cagr_df = calculate_cagr(
        nav_df
    )

    std_df = (
        calculate_standard_deviation(
            returns_df
        )
    )

    sharpe_df = (
        calculate_sharpe_ratio(
            returns_df,
            std_df,
        )
    )

    sortino_df = (
        calculate_sortino_ratio(
            returns_df
        )
    )

    alpha_beta_df = (
        calculate_alpha_beta(
            returns_df,
            benchmark_df,
        )
    )

    max_dd_df = (
        calculate_max_drawdown(
            nav_df
        )
    )

    # --------------------------------------------------------
    # Comparison table
    # --------------------------------------------------------

    comparison_df = (
        build_comparison_table(
            fund_master,
            scheme_perf,
            cagr_df,
            std_df,
            sharpe_df,
            sortino_df,
            alpha_beta_df,
            max_dd_df,
        )
    )

    # --------------------------------------------------------
    # Fund scorecard
    # --------------------------------------------------------

    scorecard_df = (
        calculate_fund_scorecard(
            comparison_df
        )
    )

    # --------------------------------------------------------
    # Tracking error
    # --------------------------------------------------------

    tracking_error_df = (
        calculate_tracking_error(
            returns_df,
            benchmark_df,
            cagr_df,
        )
    )

    # --------------------------------------------------------
    # Best / worst by category
    # --------------------------------------------------------

    best_worst_df = (
        calculate_best_worst_by_category(
            comparison_df
        )
    )

    # --------------------------------------------------------
    # Category performance
    # --------------------------------------------------------

    category_df = (
        calculate_category_performance(
            comparison_df
        )
    )

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print(
        "PERFORMANCE ANALYTICS COMPLETE"
    )
    print("=" * 70)

    print(
        f"\nFunds analysed: "
        f"{comparison_df['amfi_code'].nunique()}"
    )

    print(
        f"Comparison table rows: "
        f"{len(comparison_df)}"
    )

    print(
        f"Scorecard rows: "
        f"{len(scorecard_df)}"
    )

    print(
        f"Categories analysed: "
        f"{comparison_df['category'].nunique()}"
    )

    print(
        "\nGenerated analytical files:"
    )

    output_files = [
        "annualised_returns.csv",
        "cagr_report.csv",
        "standard_deviation.csv",
        "sharpe_values.csv",
        "sortino_values.csv",
        "alpha_beta.csv",
        "max_drawdown.csv",
        "comparison_table.csv",
        "fund_scorecard.csv",
        "tracking_error.csv",
        "best_worst_by_category.csv",
        "category_performance.csv",
    ]

    for filename in output_files:

        output_path = (
            ANALYSIS_DIR / filename
        )

        if output_path.exists():

            print(
                f"  SUCCESS: {filename}"
            )

        else:

            print(
                f"  FAILED: {filename} "
                "(NOT FOUND)"
            )

    print(
        "\nDone."
    )


# ============================================================
# SCRIPT MAIN
# ============================================================

if __name__ == "__main__":
    main()