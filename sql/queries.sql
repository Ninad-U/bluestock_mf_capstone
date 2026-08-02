-- 1. Top 5 Funds by AUM

SELECT
    scheme_name,
    aum_crore
FROM fact_performance
ORDER BY aum_crore DESC
LIMIT 5;

-- 2. Average NAV by Month

SELECT
    strftime('%Y-%m', date) AS month,
    ROUND(AVG(nav), 2) AS average_nav
FROM fact_nav
GROUP BY month
ORDER BY month;

-- 3. Monthly SIP Inflows

SELECT
    month,
    sip_inflow_crore,
    yoy_growth_pct
FROM fact_sip_inflows
ORDER BY month;

-- 4. Transactions by State

SELECT
    state,
    COUNT(*) AS total_transactions
FROM fact_transactions
GROUP BY state
ORDER BY total_transactions DESC;

-- 5. Funds with Expense Ratio below 1%

SELECT
    scheme_name,
    expense_ratio_pct
FROM fact_performance
WHERE expense_ratio_pct < 1
ORDER BY expense_ratio_pct;

-- 6. Number of Funds by Category

SELECT
    category,
    COUNT(*) AS total_funds
FROM dim_fund
GROUP BY category
ORDER BY total_funds DESC;

-- 7. Average 3-Year Return by Category

SELECT
    category,
    ROUND(AVG(return_3yr_pct), 2) AS avg_return
FROM fact_performance
GROUP BY category
ORDER BY avg_return DESC;

-- 8. Total Investment Amount by Transaction Type

SELECT
    transaction_type,
    SUM(amount_inr) AS total_amount
FROM fact_transactions
GROUP BY transaction_type;

-- 9. Top 10 Holdings by Portfolio Weight

SELECT
    stock_name,
    sector,
    weight_pct
FROM fact_portfolio_holdings
ORDER BY weight_pct DESC
LIMIT 10;

-- 10. Benchmark Closing Value Trend

SELECT
    date,
    index_name,
    close_value
FROM fact_benchmark
ORDER BY date;