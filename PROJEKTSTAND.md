# DKV-Checker - Projektstand

**Datum:** 2026-02-01

---

## Erledigte Aufgaben

### 1. Software-Anpassungen
- [x] Fahrzeugverwaltung in Einstellungen (als Sub-Tab) korrigiert
- [x] Spenden-Hinweise eingebaut (PayPal: christiansauer87)
  - Sidebar (dezent)
  - Nach erfolgreichem Import
  - Einstellungen → Über (mit PayPal-Button)
- [x] Datenschutz-Hinweise hinzugefügt
  - Einstellungen → Über → Datenschutzhinweise (ausklappbar)
  - Hilfe-Tab → Datenschutz & DSGVO
- [x] Vollständige Dokumentation als "Hilfe"-Tab integriert
  - Benutzerhandbuch
  - Alle Funktionen erklärt
  - FAQ
  - Ohne Login zugänglich
- [x] Docker-Unterstützung vorbereitet
  - Umgebungsvariable DKV_DATA_DIR für Datenverzeichnis

### 2. Docker-Dateien erstellt
- [x] `Dockerfile` - Image-Definition
- [x] `docker-compose.yml` - Einfaches Deployment
- [x] `.dockerignore` - Build-Optimierung

### 3. Docker-Image gebaut und gepusht
- [x] Image lokal gebaut: `acesco/dkv-checker:latest`
- [x] Auf GitHub Container Registry gepusht:
  - `ghcr.io/christiansauervireq/dkv-checker:latest`
  - `ghcr.io/christiansauervireq/dkv-checker:1.0`

---

## Offene Aufgaben

### Docker Hub Push (Problem)
Das Pushen zu Docker Hub funktioniert nicht (Access Denied), obwohl:
- Login erfolgreich (mit Access Token)
- Repository manuell erstellt
- Benutzername korrekt: `acesco`

**Mögliche Lösungen:**
1. Neuen Docker Hub Account erstellen
2. Docker Hub Support kontaktieren
3. Anderen Namespace/Organisation verwenden

### Synology Installation
GitHub Container Registry (ghcr.io) wird von Synology Container Manager nicht direkt unterstützt.

**Lösungen für später:**
1. Docker Hub zum Laufen bringen (bevorzugt für Synology)
2. Image als .tar exportieren und manuell laden:
   ```bash
   # Auf Mac:
   docker save ghcr.io/christiansauervireq/dkv-checker:latest -o dkv-checker.tar
   # Auf Synology:
   docker load -i dkv-checker.tar
   ```
3. Per SSH auf Synology direkt pullen:
   ```bash
   sudo docker pull ghcr.io/christiansauervireq/dkv-checker:latest
   ```

---

## Befehle für später

### Image neu bauen (nach Code-Änderungen)
```bash
cd /Users/christiansauer/Desktop/dkv-checker
docker build -t ghcr.io/christiansauervireq/dkv-checker:latest .
```

### Zu GitHub Container Registry pushen
```bash
# Login (Token von https://github.com/settings/tokens)
echo "DEIN_TOKEN" | docker login ghcr.io -u christiansauervireq --password-stdin

# Push
docker push ghcr.io/christiansauervireq/dkv-checker:latest
```

### Lokal testen
```bash
docker run -d -p 8501:8501 -v ./data:/data --name dkv-test ghcr.io/christiansauervireq/dkv-checker:latest
# Öffnen: http://localhost:8501
```

### Auf Synology (per SSH)
```bash
sudo docker pull ghcr.io/christiansauervireq/dkv-checker:latest
sudo docker run -d -p 8501:8501 -v /volume1/docker/dkv-checker/data:/data --name dkv-checker ghcr.io/christiansauervireq/dkv-checker:latest
```

---

## Accounts & Links

| Dienst | Benutzername | Link |
|--------|--------------|------|
| Docker Hub | acesco | https://hub.docker.com/u/acesco |
| GitHub | christiansauervireq | https://github.com/christiansauervireq |
| GitHub Package | - | https://github.com/christiansauervireq?tab=packages |
| PayPal Spenden | - | https://www.paypal.com/paypalme/christiansauer87 |

---

## Nächste Schritte

1. **Docker Hub Problem lösen** oder alternativen Account erstellen
2. **Package auf GitHub öffentlich machen** (falls noch nicht geschehen)
3. **Auf Synology testen** (per SSH oder nach Docker Hub Fix)
4. **Anleitung für Endnutzer erstellen** (wie man es auf verschiedenen Plattformen installiert)
