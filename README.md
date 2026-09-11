### EQUALS - KGL_Django

Dieses Projekt ist ein Webui Projekt auf Basis von Django. Es dient zur Verwaltung der Datenauswertung von den Fragebögen.

## Voraussetzungen

Stelle sicher, dass du folgende Tools installiert hast:

- **Python 3.12+**
    
- **WSL (Ubuntu)** (falls unter Windows gearbeitet wird)
    
- **PostgreSQL** (wird im Setup-Prozess auf dem Linux/WSL-System installiert)
    
- **Git**
    

## Setup-Anleitung

Befolge diese Schritte, um das Projekt lokal auf deinem Rechner einzurichten:

### 1. Repository clonen

Bash

```
git clone https://github.com/ypbautista/KGL_Django
cd KGL_Django
```

### 2. Virtuelle Umgebung erstellen

Bash

```
python3 -m venv venv
```

### 3. Umgebung aktivieren

Unter WSL/Linux/macOS:

Bash

```
source venv/bin/activate
```

### 4. Abhängigkeiten installieren

Bash

```
pip install -r requirements.txt
```

### 5. Umgebungsvariablen (.env) einrichten

Kopiere die Beispiel-Datei `.env.example`, um deine persönliche `.env`-Datei für lokale Einstellungen zu erstellen:

```
bash
cp .env.example .env
```

Öffne die neu erstellte `.env`-Datei in deinem Code-Editor und trage dort dein gewähltes Datenbank-Passwort (`DB_PASSWORD`) und optional einen lokalen `SECRET_KEY`.



Neuen SECRET_KEY generieren (optional für Lokal, erforderlich für Production)
Um einen neuen, kryptografisch sicheren SECRET_KEY zu erzeugen, führe folgenden Befehl in deinem aktivierten Terminal aus:

```
Bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```
Kopiere die generierte Zeichenkette und ersetze den Wert in deiner .env-Datei:

Code-Snippet
SECRET_KEY=dein_neu_generierter_schluessel

> ⚠️ **Wichtig:** Die Datei `.env` enthält sensible Zugangsdaten und darf **niemals** in Git committet werden! Stelle sicher, dass `.env` in deiner `.gitignore`-Datei aufgeführt ist.

### 6. PostgreSQL Datenbank aufsetzen

Da das Projekt PostgreSQL nutzt, muss der Datenbank-Server lokal gestartet und eingerichtet werden:

1. **PostgreSQL installieren & starten (falls noch nicht geschehen):**
    
    Bash
    
    ```
    sudo apt update
    sudo apt install postgresql postgresql-contrib
    sudo service postgresql start
    ```
    
2. **Datenbank und User anlegen:** Melde dich in der Postgres-Konsole an:
    
    Bash
    
    ```
    sudo -i -u postgres psql
    ```
    
    Führe im interaktiven Prompt (`postgres=#`) folgende Befehle aus (ersetze `'dein_passwort'` mit dem Passwort aus deiner `settings.py`):
    
    SQL

    (Befehle einzeln eingeben!)
    ```
	    CREATE USER kgl WITH PASSWORD 'dein_passwort' CREATEDB;
	    CREATE DATABASE kgl_db OWNER kgl;
    \c kgl_db
    GRANT ALL ON SCHEMA public TO kgl;
    ALTER SCHEMA public OWNER TO kgl;
    \q
    ```
    

### 7. Datenbank-Migrationen ausführen

Erstelle die Tabellen für die Django-Core-Funktionen und die Fragebogen-App:

Bash

```
python manage.py makemigrations
python manage.py migrate
```

### 8. Admin-Konto erstellen

Um auf das Django-Admin-Interface zuzugreifen, erstelle einen Superuser:

Bash

```
python manage.py createsuperuser
```

### 9. Server starten

Bash

```
python manage.py runserver localhost:8000
```

Die Seite ist nun unter [http://localhost:8000/admin] (http://localhost:8000/admin) oder [http://localhost:8000/portal/dashboard] (http://localhost:8000/portal/dashboard)  erreichbar.

