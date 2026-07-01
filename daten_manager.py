import json
import os
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# --- NEU: Supabase Verbindung aufbauen ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

# Veraltet, behalten wir nur als Platzhalter für Kompatibilität mit der Hauptdatei
def setze_datei_pfad(headless):
    pass

# --- NEU: Holt die echten Daten live aus Supabase ---
def lade_daten():
    try:
        # 1. Spieler laden
        spieler_response = supabase.table("spieler").select("*").execute()
        spieler_dict = {}
        for s in spieler_response.data:
            spieler_dict[s["name"]] = {
                "pin": s.get("pin") or START_PLATZHALTER_PIN,
                "ist_vereinsspieler": s.get("ist_vereinsspieler", False),
                "lizenznummer": s.get("lizenznummer", ""),
                "verein": s.get("verein", "")
            }
        
        # 2. Spiele-Historie laden
        spiele_response = supabase.table("spiele").select("*").order("id", desc=False).execute()
        spiele_historie = []
        for sp in spiele_response.data:
            spiele_historie.append({
                "Zeitstempel": sp.get("zeitstempel", ""),
                "Spieltyp": sp.get("spieltyp", ""),
                "Team A": sp.get("team_a", []),
                "Punkte A": sp.get("punkte_a", 0),
                "Team B": sp.get("team_b", []),
                "Punkte B": sp.get("punkte_b", 0),
                "EingetragenVon": sp.get("eingetragen_von", "")
            })
            
        # 3. Warteschlange laden
        warteschlange_response = supabase.table("warteschlange").select("*").execute()
        warteschlange = []
        for w in warteschlange_response.data:
            warteschlange.append({
                "Zeitstempel": w.get("zeitstempel", ""),
                "Spieltyp": w.get("spieltyp", ""),
                "Team A": w.get("team_a", []),
                "Punkte A": w.get("punkte_a", 0),
                "Team B": w.get("team_b", []),
                "Punkte B": w.get("punkte_b", 0),
                "EingetragenVon": w.get("eingetragen_von", "")
            })

        return {
            "spieler": spieler_dict,
            "spiele_historie": spiele_historie,
            "warteschlange": warteschlange
        }
    except Exception as e:
        st.error(f"Fehler beim Laden aus Supabase: {e}")
        return {"spieler": {}, "spiele_historie": [], "warteschlange": []}

# --- NEU: Schreibt Änderungen (z.B. neue Profile, Spiele oder Warteschlangen-Updates) zurück ---
def speichere_daten(daten):
    try:
        # 1. Spieler synchronisieren (upsert fügt hinzu oder aktualisiert)
        for name, info in daten["spieler"].items():
            spieler_daten = {
                "name": name,
                "pin": info.get("pin", START_PLATZHALTER_PIN),
                "ist_vereinsspieler": info.get("ist_vereinsspieler", False),
                "lizenznummer": info.get("lizenznummer", ""),
                "verein": info.get("verein", "")
            }
            supabase.table("spieler").upsert(spieler_daten, on_conflict="name").execute()

        # 2. Spiele-Historie synchronisieren
        # Da historische Spiele sich nicht ändern, laden wir die IDs und fügen nur neue hinzu
        aktuelle_db_spiele = supabase.table("spiele").select("zeitstempel, team_a").execute()
        db_keys = {(s["zeitstempel"], tuple(s["team_a"])) for s in aktuelle_db_spiele.data}
        
        for spiel in daten["spiele_historie"]:
            key = (spiel.get("Zeitstempel"), tuple(spiel.get("Team A", [])))
            if key not in db_keys:
                spiele_daten = {
                    "zeitstempel": spiel.get("Zeitstempel"),
                    "spieltyp": spiel.get("Spieltyp"),
                    "team_a": spiel.get("Team A"),
                    "punkte_a": spiel.get("Punkte A"),
                    "team_b": spiel.get("Team B"),
                    "punkte_b": spiel.get("Punkte B"),
                    "eingetragen_von": spiel.get("EingetragenVon")
                }
                supabase.table("spiele").insert(spiele_daten).execute()

        # 3. Warteschlange komplett neu schreiben
        # Am einfachsten: Warteschlange leeren und aktuellen Stand eintragen
        supabase.table("warteschlange").delete().neq("id", 0).execute()
        for w in daten["warteschlange"]:
            w_daten = {
                "zeitstempel": w.get("Zeitstempel"),
                "spieltyp": w.get("Spieltyp"),
                "team_a": w.get("Team A"),
                "punkte_a": w.get("Punkte A"),
                "team_b": w.get("Team B"),
                "punkte_b": w.get("Punkte B"),
                "eingetragen_von": w.get("EingetragenVon")
            }
            supabase.table("warteschlange").insert(w_daten).execute()

    except Exception as e:
        st.error(f"Fehler beim Speichern in Supabase: {e}")

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
    
    if df.empty:
        df = pd.DataFrame(columns=["Platz", "Spieler", "VollerName", "Elo", "Spiele", "Siege", "Niederlagen", "Differenz", "Form"])
        return df, rangliste

    df["Elo"] = df["Elo"].round(1)
    df = df.sort_values(by=["Elo", "Differenz"], ascending=[False, False]).reset_index()
    df.rename(columns={"index": "VollerName"}, inplace=True)
    df["Spieler"] = df["VollerName"].apply(kuerze_name)
    df.insert(0, "Platz", range(1, len(df) + 1))
    
    return df, rangliste