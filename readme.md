# Portfolio Dashboard

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Use
1. Open the app in your browser.
2. Upload your portfolio CSV.
3. View current pricing, allocation, and gains.
4. Download the enriched CSV.

## Notes
- Designed for a file upload workflow.
- Uses yfinance for current quote lookup.
- Cached quote data refreshes every 5 minutes.