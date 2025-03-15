# Spuštění backendu
Start-Process -NoNewWindow powershell -ArgumentList "cd backend; uvicorn main:app --reload"

# Spuštění frontendu
Start-Process -NoNewWindow powershell -ArgumentList "cd frontend; streamlit run app.py" 