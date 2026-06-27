import json
import os
import pandas as pd

if os.config.get_option if hasattr(os, "config") else False:  # Streamlit check via Hauptdatei abgefangen
    DATEI_PFAD = "petanque_daten_PROD.json"
else:
    # Standard-Fallback, Steuerung erfolgt dynamisch
    DATEI_PFAD = "petanque_daten_PROD.json" 

import streamlit as st

# Statt fester Texte holen wir die Daten jetzt sicher aus den Secrets:
ADMIN_PASSWORT = st.secrets["ADMIN_PASSWORT"]
MASTER_PIN = st.secrets["MASTER_PIN"]
START_PLATZHALTER_PIN = "PROFIL_SPERRE_INIT_2026"
K_FAKTOR = 24

def kuerze_name(voller_name):
    teile = voller_name.strip().split()
    if len(teile) > 1:
        return f"{teile[0]} {teile[-1][0]}."
    return voller_name

def setze_datei_pfad(headless):
    global DATEI_PFAD
    DATEI_PFAD = "petanque_daten_PROD.json" if headless else "petanque_daten_TEST.json"

def lade_daten():
    if os.path.exists(DATEI_PFAD):
        with open(DATEI_PFAD, "r", encoding="utf-8") as f:
            daten = json.load(f)
            if isinstance(daten.get("spieler"), list):
                daten["spieler"] = {s: {"pin": START_PLATZHALTER_PIN} for s in daten["spieler"]}
            
            # --- NEU: Bestehende Spieler um alle neuen Profilfelder erweitern ---
            for s in daten["spieler"]:
                if "ist_vereinsspieler" not in daten["spieler"][s]:
                    daten["spieler"][s]["ist_vereinsspieler"] = False
                if "lizenznummer" not in daten["spieler"][s]:
                    daten["spieler"][s]["lizenznummer"] = ""
                if "verein" not in daten["spieler"][s]:
                    daten["spieler"][s]["verein"] = ""
                    
            if "warteschlange" not in daten:
                daten["warteschlange"] = []
            return daten
    return {"spieler": {}, "spiele_historie": [], "warteschlange": []}

def speichere_daten(daten):
    with open(DATEI_PFAD, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)

def berechne_rangliste(spiele_historie, spieler_namen):
    rangliste = {s: {"Elo": 1000.0, "Spiele": 0, "Siege": 0, "Niederlagen": 0, "Differenz": 0, "Form": []} for s in spieler_namen}
    
    for spiel in spiele_historie:
        ta, tb = spiel["Team A"], spiel["Team B"]
        pa, pb = spiel["Punkte A"], spiel["Punkte B"]
        
        elo_team_a = sum(rangliste[s]["Elo"] for s in ta if s in rangliste) / max(len(ta), 1)
        elo_team_b = sum(rangliste[s]["Elo"] for s in tb if s in rangliste) / max(len(tb), 1)
        erwartung_a = 1 / (1 + 10 ** ((elo_team_b - elo_team_a) / 400))
        erwartung_b = 1 - erwartung_a
        ergebnis_a = 1.0 if pa > pb else 0.0
        ergebnis_b = 1.0 - ergebnis_a
        aenderung_a = K_FAKTOR * (ergebnis_a - erwartung_a)
        aenderung_b = K_FAKTOR * (ergebnis_b - erwartung_b)
        
        for s in ta:
            if s in rangliste:
                rangliste[s]["Elo"] += aenderung_a
                rangliste[s]["Spiele"] += 1
                rangliste[s]["Siege"] += int(ergebnis_a)
                rangliste[s]["Niederlagen"] += int(ergebnis_b)
                rangliste[s]["Differenz"] += (pa - pb)
                rangliste[s]["Form"].append("✅" if ergebnis_a == 1.0 else "❌")
        for s in tb:
            if s in rangliste:
                rangliste[s]["Elo"] += aenderung_b
                rangliste[s]["Spiele"] += 1
                rangliste[s]["Siege"] += int(ergebnis_b)
                rangliste[s]["Niederlagen"] += int(ergebnis_a)
                rangliste[s]["Differenz"] += (pb - pa)
                rangliste[s]["Form"].append("✅" if ergebnis_b == 1.0 else "❌")

    df = pd.DataFrame.from_dict(rangliste, orient='index')
    
    # 🛑 NEU: Fehler abfangen, wenn noch gar keine Spieler existieren
    if df.empty:
        # Wir bauen einfach eine leere Hülle mit den richtigen Spaltennamen
        df = pd.DataFrame(columns=["Platz", "Spieler", "VollerName", "Elo", "Spiele", "Siege", "Niederlagen", "Differenz", "Form"])
        return df, rangliste

    # Wenn Spieler da sind, ganz normal berechnen:
    df["Elo"] = df["Elo"].round(1)
    df = df.sort_values(by=["Elo", "Differenz"], ascending=[False, False]).reset_index()
    df.rename(columns={"index": "VollerName"}, inplace=True)
    df["Spieler"] = df["VollerName"].apply(kuerze_name)
    df.insert(0, "Platz", range(1, len(df) + 1))
    
    return df, rangliste