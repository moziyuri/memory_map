# MemoryMap Frontend

Toto je frontend aplikace pro MemoryMap - aplikaci, která umožňuje ukládat a vizualizovat vzpomínky na mapě.

## Požadavky

- Python 3.7 nebo vyšší
- Streamlit 1.32.0 nebo vyšší
- Další závislosti uvedené v `requirements.txt`

## Instalace

1. Nainstalujte všechny závislosti:
   ```bash
   pip install -r requirements.txt
   ```

## Spuštění aplikace

### Windows - PowerShell

Nejjednodušší způsob spuštění aplikace je pomocí PowerShell skriptu:

```
.\launch.ps1
```

### Windows - Batch

Alternativně můžete použít batch soubor:

```
launch.bat
```

### Manuální spuštění

```bash
streamlit run app.py --server.port=8501 --server.address=localhost
```

## Poznámky ke spuštění

- Ujistěte se, že backend API běží na adrese `http://localhost:8000` před spuštěním frontendu
- Streamlit frontend bude dostupný na adrese `http://localhost:8501`
- Pokud se aplikace nespustí správně, zkontrolujte chybové hlášení v konzoli

## Řešení problémů

1. **Problém s instalací balíčků**
   - Zkuste ručně nainstalovat balíčky: `pip install -r requirements.txt`
   - Ujistěte se, že používáte Python 3.7+

2. **Backend není dostupný**
   - Ověřte, že backend běží na `http://localhost:8000`
   - V konzoli byste měli vidět "Uvicorn running on http://localhost:8000"

3. **Streamlit se nespustí**
   - Zkontrolujte, zda je Streamlit nainstalován: `pip show streamlit`
   - Zkuste spustit Streamlit ručně: `streamlit hello` pro ověření instalace

4. **Prohlížeč nezobrazuje aplikaci**
   - Ručně otevřete `http://localhost:8501` v prohlížeči
   - Zkontrolujte, zda váš firewall neblokuje port 8501

## Kontakt

Pro další pomoc nebo dotazy kontaktujte správce aplikace. 