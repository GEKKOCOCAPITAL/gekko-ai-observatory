.PHONY: install run test app
install: ; pip install -e ".[app,dev]"
run: ; luxfin run
test: ; pytest -q --junitxml=outputs/test_results.xml
app: ; streamlit run app/streamlit_app.py
