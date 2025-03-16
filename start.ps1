# Aktivace virtuálního prostředí
.\venv\Scripts\activate

# Spuštění backendu v novém okně
Start-Process powershell -ArgumentList "-NoExit -Command cd backend; uvicorn main:app --reload"

# Spuštění frontendu
cd frontend
streamlit run app.py 