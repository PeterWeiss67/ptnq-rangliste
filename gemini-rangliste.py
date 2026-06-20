import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

st.set_page_config(layout="wide", page_title="Petanque Elo-Rangliste", page_icon="🏆")

DATEI_PFAD = "petanque_daten.json"
# 🔐 HIER DEIN WUNSCH-PASSWORT EINTRAGEN:
ADMIN_PASSWORT = "petanque2026"

def lade_daten():
    if os.path.exists(DATEI_PFAD):
        with open(DATEI_PFAD, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"spieler": ["Ali", "Beatrix", "Charly", "Doris", "Emil", "Frida"], "spiele_historie": []}

def speichere_daten(daten):
    with open(DATEI_PFAD, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)

gespeicherte_daten = lade_daten()

if 'spieler' not in st.session_state:
    sortierte_spieler = gespeicherte_daten["spieler"]
    sortierte_spieler.sort()
    st.session_state.spieler = sortierte_spieler

if 'spiele_historie' not in st.session_state:
    st.session_state.spiele_historie = gespeicherte_daten["spiele_historie"]

st.title("🧮 Petanque Rangliste & Vereins-Elo 🏆")

# --- SEITENLEISTE: LOGO & ADMIN-LOGIN ---
with st.sidebar:
    st.image("ptnq_logo.svg", use_container_width=True)
    st.divider()
    
    st.header("🔒 Admin-Bereich")
    # Passwort-Eingabefeld (verdeckt die Zeichen mit Punkten)
    pwd_eingabe = st.text_input("Admin-Passwort eingeben, um Schreibrechte freizuschalten:", type="password")
    
    # Überprüfung, ob das Passwort korrekt ist
    ist_admin = (pwd_eingabe == ADMIN_PASSWORT)
    
    if ist_admin:
        st.success("🔓 Schreibrechte aktiv!")
    elif pwd_eingabe:
        st.error("❌ Falsches Passwort.")
        
    st.divider()
    
    # Spieler verwalten nur für Admins sichtbar
    if ist_admin:
        st.header("👥 Spieler verwalten")
        neuer_spieler = st.text_input("Neuer Spieler Name:")
        if st.button("Spieler hinzufügen", use_container_width=True):
            if neuer_spieler and neuer_spieler not in st.session_state.spieler:
                st.session_state.spieler.append(neuer_spieler)
                st.session_state.spieler.sort()
                speichere_daten({"spieler": st.session_state.spieler, "spiele_historie": st.session_state.spiele_historie})
                st.success(f"{neuer_spieler} hinzugefügt!")
                st.rerun()

# --- HAUPTLAYOUT: ZWEI SPALTEN ---
layout_links, layout_rechts = st.columns([2, 3])

# LINKE SEITE: EINGABEMASKE (Nur für Admins freigeschaltet!)
with layout_links:
    st.header("🎯 Spiel eintragen")
    
    if ist_admin:
        with st.container(border=True):
            spieltyp = st.selectbox(
                "📍 Spieltyp / Wertung wählen",
                ["🌳 Hobby / Park", "🏟️ Verein / Training", "🏆 Liga", "🥇 Turnier"]
            )
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Team A")
                team_a = st.multiselect("Spieler Team A (1-3)", st.session_state.spieler, key="ta")
                punkte_a = st.number_input("Punkte Team A", min_value=0, max_value=13, value=0, step=1, key="pa")
            with col2:
                st.subheader("Team B")
                verfuegbar_b = [s for s in st.session_state.spieler if s not in team_a]
                team_b = st.multiselect("Spieler Team B (1-3)", verfuegbar_b, key="tb")
                punkte_b = st.number_input("Punkte Team B", min_value=0, max_value=13, value=0, step=1, key="pb")

            if st.button("Ergebnis speichern", type="primary", use_container_width=True):
                if not team_a or not team_b:
                    st.error("Beide Teams müssen mindestens einen Spieler haben!")
                elif punkte_a == punkte_b:
                    st.error("Beim Petanque gibt es kein Unentschieden!")
                else:
                    jetzt = datetime.now().strftime("%d.%m.%Y %H:%M")
                    
                    st.session_state.spiele_historie.append({
                        "Zeitstempel": jetzt,
                        "Spieltyp": spieltyp,
                        "Team A": team_a, "Punkte A": punkte_a,
                        "Team B": team_b, "Punkte B": punkte_b
                    })
                    speichere_daten({"spieler": st.session_state.spieler, "spiele_historie": st.session_state.spiele_historie})
                    st.success("Spiel erfolgreich eingetragen!")
                    st.rerun()
    else:
        # Hinweis für normale User
        st.info("ℹ️ Um Spiele einzutragen oder Spieler hinzuzufügen, musst du das Admin-Passwort in der linken Seitenleiste eingeben.")

# RECHTE SEITE: INTERAKTIVE TABELLE (Immer für alle sichtbar!)
with layout_rechts:
    st.header("📊 Die aktuelle Tabelle")

    rangliste = {s: {"Elo": 1000.0, "Spiele": 0, "Siege": 0, "Niederlagen": 0, "Differenz": 0} for s in st.session_state.spieler}

    for spiel in st.session_state.spiele_historie:
        ta, tb = spiel["Team A"], spiel["Team B"]
        pa, pb = spiel["Punkte A"], spiel["Punkte B"]
        typ = spiel.get("Spieltyp", "🏟️ Verein / Training")
        
        if "Hobby" in typ:
            k_faktor = 12
        elif "Liga" in typ:
            k_faktor = 36
        elif "Turnier" in typ:
            k_faktor = 48
        else:
            k_faktor = 24
        
        elo_team_a = sum(rangliste[s]["Elo"] for s in ta if s in rangliste) / len(ta)
        elo_team_b = sum(rangliste[s]["Elo"] for s in tb if s in rangliste) / len(tb)
        
        erwartung_a = 1 / (1 + 10 ** ((elo_team_b - elo_team_a) / 400))
        erwartung_b = 1 - erwartung_a
        
        ergebnis_a = 1.0 if pa > pb else 0.0
        ergebnis_b = 1.0 - ergebnis_a
        
        aenderung_a = k_faktor * (ergebnis_a - erwartung_a)
        aenderung_b = k_faktor * (ergebnis_b - erwartung_b)
        
        for s in ta:
            if s in rangliste:
                rangliste[s]["Elo"] += aenderung_a
                rangliste[s]["Spiele"] += 1
                rangliste[s]["Siege"] += int(ergebnis_a)
                rangliste[s]["Niederlagen"] += int(ergebnis_b)
                rangliste[s]["Differenz"] += (pa - pb)
                
        for s in tb:
            if s in rangliste:
                rangliste[s]["Elo"] += aenderung_b
                rangliste[s]["Spiele"] += 1
                rangliste[s]["Siege"] += int(ergebnis_b)
                rangliste[s]["Niederlagen"] += int(ergebnis_a)
                rangliste[s]["Differenz"] += (pb - pa)

    df = pd.DataFrame.from_dict(rangliste, orient='index')
    df["Elo"] = df["Elo"].round(1)
    df = df.sort_values(by=["Elo", "Differenz"], ascending=[False, False])

    df.index.name = "Spieler"
    df = df.reset_index()
    df.insert(0, "Platz", range(1, len(df) + 1))

    st.data_editor(
        df, 
        use_container_width=True, 
        disabled=True,
        hide_index=True,
        column_config={
            "Platz": st.column_config.NumberColumn("🏆 Platz", format="%d"),
            "Spieler": st.column_config.TextColumn("👤 Spieler"),
            "Elo": st.column_config.NumberColumn("Elo-Punkte", format="%.1f 🔥"),
            "Differenz": st.column_config.NumberColumn("± Kugeln")
        }
    )

st.divider()

# --- 3. HISTORIE ANZEIGEN & LÖSCHEN ---
if st.session_state.spiele_historie:
    st.header("📄 Spiele-Historie")
    
    # Löschen-Funktion nur einblenden, wenn man Admin ist!
    if ist_admin:
        with st.container(border=True):
            st.subheader("❌ Einzelnes Spiel löschen")
            spiel_optionen = []
            for i, s in enumerate(st.session_state.spiele_historie):
                spiel_text = f"Spiel {i+1} ({s.get('Zeitstempel', 'Unbekannt')}): {', '.join(s['Team A'])} ({s['Punkte A']}:{s['Punkte B']}) {', '.join(s['Team B'])}"
                spiel_optionen.append((i, spiel_text))
            
            ausgewaehltes_spiel = st.selectbox(
                "Wähle das Spiel aus, das gelöscht werden soll:",
                options=spiel_optionen,
                format_func=lambda x: x[1]
            )
            
            if st.button("❌ Ausgewähltes Spiel unwiderruflich löschen", type="secondary", use_container_width=True):
                index_zu_loeschen = ausgewaehltes_spiel[0]
                st.session_state.spiele_historie.pop(index_zu_loeschen)
                speichere_daten({"spieler": st.session_state.spieler, "spiele_historie": st.session_state.spiele_historie})
                st.success(f"Spiel {index_zu_loeschen + 1} wurde gelöscht!")
                st.rerun()

    # Spiele-Liste (Für alle sichtbar)
    with st.expander("🔍 Alle bisherigen Spiele detailliert anzeigen"):
        schoene_historie = []
        for i, s in enumerate(st.session_state.spiele_historie):
            schoene_historie.append({
                "Nr.": i + 1,
                "Datum / Uhrzeit": s.get("Zeitstempel", "Unbekannt"),
                "Typ": s.get("Spieltyp", "🏟️ Verein / Training"),
                "Team A": ", ".join(s["Team A"]),
                "Ergebnis": f"{s['Punkte A']} : {s['Punkte B']}",
                "Team B": ", ".join(s["Team B"])
            })
        st.table(schoene_historie)
        
    # Komplett-Reset nur für Admins sichtbar
    if ist_admin:
        with st.expander("⚠️ Gefahrenzone: Gesamtes Turnier löschen"):
            if st.button("Gesamtes Turnier / Alle Daten löschen", type="primary", use_container_width=True):
                if os.path.exists(DATEI_PFAD):
                    os.remove(DATEI_PFAD)
                st.session_state.spiele_historie = []
                st.success("Alle Daten wurden gelöscht!")
                st.rerun()