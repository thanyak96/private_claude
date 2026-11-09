# tt – TimeTac Zeiterfassung im Terminal

Kleines Python-CLI (nur Standardbibliothek) für die TimeTac REST API v3.

## Einrichtung

```bash
export TIMETAC_ACCOUNT=<account>          # wie in https://go.timetac.com/<account>
export TIMETAC_TOKEN=<oauth2-access-token>
```

Alternativ statt `TIMETAC_TOKEN` den OAuth2 Password-Grant verwenden:
`TIMETAC_CLIENT_ID`, `TIMETAC_CLIENT_SECRET`, `TIMETAC_USERNAME`, `TIMETAC_PASSWORD`.
API-Zugang (Client-ID/Secret) vergibt der TimeTac-Admin bzw. der TimeTac-Support.

Falls eure Instanz andere URLs nutzt: `TIMETAC_API_BASE` und `TIMETAC_TOKEN_URL` überschreiben.

## Verwendung

```bash
python3 timetac/tt.py me              # wer bin ich
python3 timetac/tt.py tasks projekt   # Tasks suchen
python3 timetac/tt.py start "Projekt X"   # Task-ID oder eindeutiger Namensteil
python3 timetac/tt.py status
python3 timetac/tt.py stop
python3 timetac/tt.py today           # heutige Buchungen + Summe
```

Tipp: `alias tt="python3 ~/private_claude/timetac/tt.py"`
