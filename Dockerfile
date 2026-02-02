# DKV Abrechnungs-Checker
# Streamlit-Anwendung zur Analyse von DKV-Tankkartenabrechnungen

FROM python:3.11-slim

# Arbeitsverzeichnis
WORKDIR /app

# System-Abhängigkeiten für pdfplumber und Healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python-Abhängigkeiten kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendung kopieren
COPY dkv_checker.py .
COPY i18n.py .
COPY handbuch.html .

# Datenverzeichnis für persistente Daten
RUN mkdir -p /data

# Streamlit-Konfiguration
RUN mkdir -p /root/.streamlit
RUN echo '[server]\n\
headless = true\n\
port = 8501\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
\n\
[browser]\n\
gatherUsageStats = false\n\
' > /root/.streamlit/config.toml

# Port freigeben
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Anwendung starten
CMD ["streamlit", "run", "dkv_checker.py", "--server.address=0.0.0.0"]
