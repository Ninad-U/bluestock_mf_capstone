-- ============================================================
-- MUTUAL FUND ANALYTICS PLATFORM - DATABASE SCHEMA
-- ============================================================
-- Purpose: SQLite database for mutual fund analytics
-- Tables: 8 (1 dimension, 7 fact tables)
-- Design: Simple star schema for easy querying and Power BI integration
-- ============================================================

-- ============================================================
-- 1. DIM_FUND - Fund Master Dimension Table
-- ============================================================
-- Purpose: Stores master information about each mutual fund scheme
-- Primary Key: amfi_code (unique fund identifier)
-- Relationships: Referenced by fact tables (nav, performance, transactions, portfolio)
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_fund (
    amfi_code           INTEGER PRIMARY KEY,
    fund_house          TEXT,
    scheme_name         TEXT,
    category            TEXT,
    sub_category        TEXT,
    plan                TEXT,
    launch_date         DATE,
    benchmark           TEXT,
    expense_ratio_pct   REAL,
    exit_load_pct       REAL,
    min_sip_amount      INTEGER,
    min_lumpsum_amount  INTEGER,
    fund_manager        TEXT,
    risk_category       TEXT,
    sebi_category_code  TEXT
);


-- ============================================================
-- 2. FACT_NAV - Historical NAV Data
-- ============================================================
-- Purpose: Daily Net Asset Value history for each fund
-- Foreign Key: amfi_code references dim_fund
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_nav (
    amfi_code   INTEGER,
    date        DATE,
    nav         REAL,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);


-- ============================================================
-- 3. FACT_PERFORMANCE - Scheme Performance Metrics
-- ============================================================
-- Purpose: Risk-return metrics and performance ratings for each fund
-- Foreign Key: amfi_code references dim_fund
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_performance (
    amfi_code           INTEGER,
    scheme_name         TEXT,
    fund_house          TEXT,
    category            TEXT,
    plan                TEXT,
    return_1yr_pct      REAL,
    return_3yr_pct      REAL,
    return_5yr_pct      REAL,
    benchmark_3yr_pct   REAL,
    alpha               REAL,
    beta                REAL,
    sharpe_ratio        REAL,
    sortino_ratio       REAL,
    std_dev_ann_pct     REAL,
    max_drawdown_pct    REAL,
    aum_crore           REAL,
    expense_ratio_pct   REAL,
    morningstar_rating  INTEGER,
    risk_grade          TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);


-- ============================================================
-- 4. FACT_TRANSACTIONS - Investor Transactions
-- ============================================================
-- Purpose: Individual investor buy/sell/SIP transactions
-- Foreign Key: amfi_code references dim_fund
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_transactions (
    investor_id         TEXT,
    transaction_date    DATE,
    amfi_code           INTEGER,
    transaction_type    TEXT,
    amount_inr          INTEGER,
    state               TEXT,
    city                TEXT,
    city_tier           TEXT,
    age_group           TEXT,
    gender              TEXT,
    annual_income_lakh  REAL,
    payment_mode        TEXT,
    kyc_status          TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);


-- ============================================================
-- 5. FACT_PORTFOLIO_HOLDINGS - Stock Holdings by Fund
-- ============================================================
-- Purpose: Detailed portfolio composition showing stocks held by each fund
-- Foreign Key: amfi_code references dim_fund
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_portfolio_holdings (
    amfi_code           INTEGER,
    stock_symbol        TEXT,
    stock_name          TEXT,
    sector              TEXT,
    weight_pct          REAL,
    market_value_cr     REAL,
    current_price_inr   REAL,
    portfolio_date      DATE,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);


-- ============================================================
-- 6. FACT_AUM - Assets Under Management by Fund House
-- ============================================================
-- Purpose: Monthly AUM data aggregated at fund house level
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_aum (
    date                DATE,
    fund_house          TEXT,
    aum_lakh_crore      REAL,
    aum_crore           REAL,
    num_schemes         INTEGER
);


-- ============================================================
-- 7. FACT_SIP_INFLOWS - Monthly SIP Trends
-- ============================================================
-- Purpose: Industry-wide SIP inflow trends and account growth
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_sip_inflows (
    month                       DATE,
    sip_inflow_crore            REAL,
    active_sip_accounts_crore   REAL,
    new_sip_accounts_lakh       REAL,
    sip_aum_lakh_crore          REAL,
    yoy_growth_pct              REAL
);


-- ============================================================
-- 8. FACT_BENCHMARK - Benchmark Index Values
-- ============================================================
-- Purpose: Daily closing values of benchmark indices
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_benchmark (
    date            DATE,
    index_name      TEXT,
    close_value     REAL
);


-- ============================================================
-- OPTIONAL: Create indexes for better query performance
-- ============================================================
-- Indexes speed up queries on commonly filtered/joined columns
-- ============================================================

-- Index for NAV queries (date range, fund lookups)
CREATE INDEX IF NOT EXISTS idx_nav_amfi_code ON fact_nav(amfi_code);
CREATE INDEX IF NOT EXISTS idx_nav_date ON fact_nav(date);

-- Index for performance lookups
CREATE INDEX IF NOT EXISTS idx_performance_amfi_code ON fact_performance(amfi_code);

-- Index for transactions (frequent date range and fund queries)
CREATE INDEX IF NOT EXISTS idx_transactions_amfi_code ON fact_transactions(amfi_code);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON fact_transactions(transaction_date);

-- Index for portfolio holdings
CREATE INDEX IF NOT EXISTS idx_portfolio_amfi_code ON fact_portfolio_holdings(amfi_code);

-- Index for AUM (date and fund house lookups)
CREATE INDEX IF NOT EXISTS idx_aum_date ON fact_aum(date);
CREATE INDEX IF NOT EXISTS idx_aum_fund_house ON fact_aum(fund_house);

-- Index for SIP (monthly trend queries)
CREATE INDEX IF NOT EXISTS idx_sip_month ON fact_sip_inflows(month);

-- Index for benchmark (date and index lookups)
CREATE INDEX IF NOT EXISTS idx_benchmark_date ON fact_benchmark(date);
CREATE INDEX IF NOT EXISTS idx_benchmark_name ON fact_benchmark(index_name);

-- ============================================================
-- END OF SCHEMA
-- ============================================================