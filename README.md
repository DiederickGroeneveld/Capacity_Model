# Capacity Model

A best-practice starter for a Streamlit-based capacity modeling application.

## What is included

- Root-level `app.py` entrypoint for Streamlit
- `src/capacity_model` package for reusable business logic
- `services` module for capacity calculations
- `data` module for sample and uploaded datasets
- Basic automated test coverage for non-UI logic

## Quick start

1. Create and activate a virtual environment.
2. Install the project in editable mode:
   ```bash
   pip install -e .[dev]
   ```
3. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```
4. Run tests:
   ```bash
   pytest
   ```

## Expected input columns

If you upload a CSV, include these columns:

- `team`
- `period`
- `capacity`
- `demand`

## Next steps

- Replace the sample dataset with your real data source
- Extend `src/capacity_model/services/capacity.py` with domain-specific rules
- Add more pages or filters once the model requirements are clearer
