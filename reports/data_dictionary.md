# Data Dictionary – Mutual Fund Analytics Platform

---

## fund_master.csv

| Column | Type |
|--------|------|
| amfi_code | Integer |
| fund_house | String |
| scheme_name | String |
| category | String |
| sub_category | String |
| plan | String |
| launch_date | Date |
| benchmark | String |
| expense_ratio_pct | Decimal |
| exit_load_pct | Decimal |
| min_sip_amount | Integer |
| min_lumpsum_amount | Integer |
| fund_manager | String |
| risk_category | String |
| sebi_category_code | String |

---

## nav_history.csv

| Column | Type |
|--------|------|
| amfi_code | Integer |
| date | Date |
| nav | Decimal |

---

## aum_by_fund_house.csv

| Column | Type |
|--------|------|
| date | Date |
| fund_house | String |
| aum_lakh_crore | Decimal |
| aum_crore | Decimal |
| num_schemes | Integer |

---

## monthly_sip_inflows.csv

| Column | Type |
|--------|------|
| month | Date |
| sip_inflow_crore | Decimal |
| active_sip_accounts_crore | Decimal |
| new_sip_accounts_lakh | Decimal |
| sip_aum_lakh_crore | Decimal |
| yoy_growth_pct | Decimal |

---

## category_inflows.csv

| Column | Type |
|--------|------|
| month | Date |
| category | String |
| net_inflow_crore | Integer |

---

## industry_folio_count.csv

| Column | Type |
|--------|------|
| month | Date |
| total_folios_crore | Decimal |
| equity_folios_crore | Decimal |
| debt_folios_crore | Decimal |
| hybrid_folios_crore | Decimal |
| others_folios_crore | Decimal |

---

## scheme_performance.csv

| Column | Type |
|--------|------|
| amfi_code | Integer |
| scheme_name | String |
| fund_house | String |
| category | String |
| plan | String |
| return_1yr_pct | Decimal |
| return_3yr_pct | Decimal |
| return_5yr_pct | Decimal |
| benchmark_3yr_pct | Decimal |
| alpha | Decimal |
| beta | Decimal |
| sharpe_ratio | Decimal |
| sortino_ratio | Decimal |
| std_dev_ann_pct | Decimal |
| max_drawdown_pct | Decimal |
| aum_crore | Decimal |
| expense_ratio_pct | Decimal |
| morningstar_rating | Integer |
| risk_grade | String |

---

## investor_transactions.csv

| Column | Type |
|--------|------|
| investor_id | String |
| transaction_date | Date |
| amfi_code | Integer |
| transaction_type | String |
| amount_inr | Integer |
| state | String |
| city | String |
| city_tier | String |
| age_group | String |
| gender | String |
| annual_income_lakh | Decimal |
| payment_mode | String |
| kyc_status | String |

---

## portfolio_holdings.csv

| Column | Type |
|--------|------|
| amfi_code | Integer |
| stock_symbol | String |
| stock_name | String |
| sector | String |
| weight_pct | Decimal |
| market_value_cr | Decimal |
| current_price_inr | Decimal |
| portfolio_date | Date |

---

## benchmark_indices.csv

| Column | Type |
|--------|------|
| date | Date |
| index_name | String |
| close_value | Decimal |