# The Shelf Is Lying

An inventory analysis project about a common retail problem: an item can appear available in the system while being difficult or impossible to find in the store.

The case study follows a fictional back-to-campus collection across 24 stores. It focuses on three connected questions:

1. When does recorded inventory overstate practical availability?
2. Are recent returns or a move to store-specific clearance locations part of the explanation?
3. Which corrective actions are worth limited store labor?

The operational data is synthetic. It is designed from explicit retail rules so that the hidden physical state is known for evaluation. It does **not** represent Target data or Target operating procedures.

## Project status

Implementation is in progress. The first milestone creates the synthetic store, product, inventory, return, pickup, markdown, and audit tables.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/generate_data.py
```

Generated CSV files are written to `data/raw/` and are intentionally excluded from Git.

