# The Shelf Is Lying

An inventory analysis project about a common retail problem: an item can appear available in the system while being difficult or impossible to find in the store.

The case study follows a fictional back-to-campus collection across 24 stores. It focuses on three connected questions:

1. When does recorded inventory overstate practical availability?
2. Are recent returns or a move to store-specific clearance locations part of the explanation?
3. Which corrective actions are worth limited store labor?

The operational data is synthetic. It is designed from explicit retail rules so that the hidden physical state is known for evaluation. It does **not** represent Target data or Target operating procedures.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/run_pipeline.py
streamlit run app.py
```

Generated CSV files are written to `data/raw/` and are intentionally excluded from Git.

## What is included

- A reproducible simulation of stores, products, inventory locations, returns, markdowns, pickup attempts, and physical audits
- A clear business-rule risk baseline and one interpretable availability model
- Store clearance fingerprints that distinguish local assortment from operational warning signs
- A recommendation policy that ranks actions by expected value under a labor budget
- A four-view Streamlit presentation and a short leadership summary

## Deliberate limits

The project does not include an API, database, cloud deployment, chatbot, or large model comparison. The code is organized around the business questions and can be read from the data generation through the recommendation.

Run the small set of business-rule checks with:

```bash
python -m unittest discover -s tests
```

