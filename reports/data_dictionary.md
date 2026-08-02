# Mutual Fund Analytics Platform - Data Dictionary

## fund_master.csv

- amfi_code
- fund_house
- scheme_name
- category
- sub_category
- plan
- launch_date
- benchmark
- expense_ratio_pct
- exit_load_pct
- min_sip_amount
- min_lumpsum_amount
- fund_manager
- risk_category
- sebi_category_code


## nav_history.csv

- amfi_code
- date
- nav


## aum_by_fund_house.csv

- date
- fund_house
- aum_lakh_crore
- aum_crore
- num_schemes


## monthly_sip_inflows.csv

- month
- sip_inflow_crore
- active_sip_accounts_crore
- new_sip_accounts_lakh
- sip_aum_lakh_crore
- yoy_growth_pct


## category_inflows.csv

- month
- category
- net_inflow_crore


## industry_folio_count.csv

- month
- total_folios_crore
- equity_folios_crore
- debt_folios_crore
- hybrid_folios_crore
- others_folios_crore


## scheme_performance.csv

- amfi_code
- scheme_name
- fund_house
- category
- plan
- return_1yr_pct
- return_3yr_pct
- return_5yr_pct
- benchmark_3yr_pct
- alpha
- beta
- sharpe_ratio
- sortino_ratio
- std_dev_ann_pct
- max_drawdown_pct
- aum_crore
- expense_ratio_pct
- morningstar_rating
- risk_grade


## investor_transactions.csv

- investor_id
- transaction_date
- amfi_code
- transaction_type
- amount_inr
- state
- city
- city_tier
- age_group
- gender
- annual_income_lakh
- payment_mode
- kyc_status


## portfolio_holdings.csv

- amfi_code
- stock_symbol
- stock_name
- sector
- weight_pct
- market_value_cr
- current_price_inr
- portfolio_date


## benchmark_indices.csv

- date
- index_name
- close_value