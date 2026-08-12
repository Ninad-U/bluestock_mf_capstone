import pandas as pd

scheme_performance = pd.read_csv(
    '../data/processed/scheme_performance_cleaned.csv'
)

# Simple fund recommender
def recommend_funds(risk_appetite):
    risk_map = {
        'Low': 'Low',
        'Moderate': 'Moderate',
        'High': 'High',
        'Very High': 'Very High'
    }
    
    if risk_appetite not in risk_map:
        return pd.DataFrame()
    
    matched_funds = scheme_performance[scheme_performance['risk_grade'] == risk_appetite].sort_values('sharpe_ratio', ascending=False)
    return matched_funds[['scheme_name', 'fund_house', 'sharpe_ratio', 'risk_grade']].head(3)

print("\n=== Fund Recommendations ===")
for risk in ['Low', 'Moderate', 'High']:
    print(f"\n{risk} Risk Appetite:")
    print(recommend_funds(risk).to_string(index=False))