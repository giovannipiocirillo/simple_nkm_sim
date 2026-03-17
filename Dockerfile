FROM python:3.10-slim

# Aggiorna i repository e installa Octave e Dynare
RUN apt-get update && apt-get install -y \
    octave \
    dynare \
    && rm -rf /var/lib/apt/lists/*

# Imposta la cartella di lavoro
WORKDIR /app

# Installa le librerie Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del codice
COPY . .

EXPOSE 7860

CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
