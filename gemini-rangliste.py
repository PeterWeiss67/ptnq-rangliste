import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# Die App bleibt für große Monitore zentriert
st.set_page_config(page_title="Petanque Elo-Rangliste", page_icon="🏆")

# --- DYNAMISCHER DATEN-SCHALTER ---
if st.config.get_option("server.headless"):
    DATEI_PFAD = "petanque_daten_PROD.json"  # Die echte Live-Datenbank im Netz
else:
    DATEI_PFAD = "petanque_daten_TEST.json"  # Deine lokale Spielwiese auf dem PC

ADMIN_PASSWORT = "petanque2026"

def lade_daten():
    if os.path.exists(DATEI_PFAD):
        with open(DATEI_PFAD, "r", encoding="utf-8") as f:
            daten = json.load(f)
            if "warteschlange" not in daten:
                daten["warteschlange"] = []
            return daten
    return {"spieler": ["Ali", "Beatrix", "Charly", "Doris", "Emil", "Frida"], "spiele_historie": [], "warteschlange": []}

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

if 'warteschlange' not in st.session_state:
    st.session_state.warteschlange = gespeicherte_daten["warteschlange"]


# --- SEITENLEISTE: PROFIL-AUSWAHL & ADMIN ---
with st.sidebar:
    # Das Logo wurde hier entfernt, da es jetzt groß auf der Hauptseite steht
    if st.config.get_option("server.headless"):
        st.caption("🟢 Live-Modus (PROD)")
    else:
        st.caption("🟡 Test-Modus (LOCAL)")
        
    st.header("👤 Mein Profil")
    aktueller_user = st.selectbox("Wer bist du?", ["Gast / Zuschauer"] + st.session_state.spieler)
    
    st.divider()
    st.header("🔒 Admin-Bereich")
    pwd_eingabe = st.text_input("Passwort für Admin-Rechte:", type="password")
    ist_admin = (pwd_eingabe == ADMIN_PASSWORT)
    
    if ist_admin:
        st.success("🔓 Admin-Rechte aktiv!")
        st.header("👥 Spieler verwalten")
        neuer_spieler = st.text_input("Neuer Spieler Name:")
        if st.button("Spieler hinzufügen", use_container_width=True):
            if neuer_spieler and neuer_spieler not in st.session_state.spieler:
                st.session_state.spieler.append(neuer_spieler)
                st.session_state.spieler.sort()
                speichere_daten({"spieler": st.session_state.spieler, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                st.success(f"{neuer_spieler} hinzugefügt!")
                st.rerun()


# ==========================================
# 1. LOGO GANZ OBEN AUF DER HAUPTSEITE
# ==========================================
st.image("ptnq_logo.svg", use_container_width=True)
st.write("") 

# ==========================================
# 2. HIER DIE TABS GENAU EINMAL DEFINIEREN
# ==========================================
tab_tabelle, tab_eintragen, tab_offene = st.tabs(["📊 Rangliste", "🎯 Spiel eintragen", "⏳ Offene Bestätigungen"])


# ==========================================
# 3. TAB 1: DIE RANGLISTE
# ==========================================
with tab_tabelle:
    st.header("Rangliste")

    rangliste = {s: {"Elo": 1000.0, "Spiele": 0, "Siege": 0, "Niederlagen": 0, "Differenz": 0} for s in st.session_state.spieler}

    for spiel in st.session_state.spiele_historie:
        ta, tb = spiel["Team A"], spiel["Team B"]
        pa, pb = spiel["Punkte A"], spiel["Punkte B"]
        typ = spiel.get("Spieltyp", "🏟️ Verein / Training")
        
        if "Hobby" in typ: k_faktor = 12
        elif "Liga" in typ: k_faktor = 36
        elif "Turnier" in typ: k_faktor = 48
        else: k_faktor = 24
        
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

    st.data_editor(df, use_container_width=True, disabled=True, hide_index=True,
        column_config={
            "Platz": st.column_config.NumberColumn("🏆 Platz", format="%d"),
            "Spieler": st.column_config.TextColumn("👤 Spieler"),
            "Elo": st.column_config.NumberColumn("Elo-Punkte", format="%.1f 🔥"),
            "Differenz": st.column_config.NumberColumn("± Kugeln")
        }
    )

    st.divider()
    
    if st.session_state.spiele_historie:
        st.subheader("📄 Bestätigte Spiele-Historie")
        
        if ist_admin:
            with st.container(border=True):
                st.caption("❌ Einzelnes Spiel löschen (Admin)")
                spiel_optionen = [(i, f"Spiel {i+1}: {', '.join(s['Team A'])} ({s['Punkte A']}:{s['Punkte B']}) {', '.join(s['Team B'])}") for i, s in enumerate(st.session_state.spiele_historie)]
                ausgewaehltes_spiel = st.selectbox("Wähle das Spiel aus:", options=spiel_optionen, format_func=lambda x: x[1])
                if st.button("❌ Spiel unwiderruflich löschen", use_container_width=True):
                    st.session_state.spiele_historie.pop(ausgewaehltes_spiel[0])
                    speichere_daten({"spieler": st.session_state.spieler, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                    st.success("Spiel gelöscht!")
                    st.rerun()

        with st.expander("🔍 Alle bestätigten Spiele anzeigen"):
            schoene_historie = [{"Nr.": i + 1, "Datum / Uhrzeit": s.get("Zeitstempel", "Unbekannt"), "Typ": s.get("Spieltyp", "🏟️ Verein / Training"), "Team A": ", ".join(s["Team A"]), "Ergebnis": f"{s['Punkte A']} : {s['Punkte B']}", "Team B": ", ".join(s["Team B"])} for i, s in enumerate(st.session_state.spiele_historie)]
            st.table(schoene_historie)
            
        if ist_admin:
            with st.expander("⚠️ Gefahrenzone: Gesamtes Turnier löschen"):
                if st.button("Gesamtes Turnier / Alle Daten löschen", type="primary", use_container_width=True):
                    if os.path.exists(DATEI_PFAD): os.remove(DATEI_PFAD)
                    st.session_state.spiele_historie = []
                    st.session_state.warteschlange = []
                    st.success("Alle Daten gelöscht!")
                    st.rerun()


# ==========================================
# 4. TAB 2: SPIEL EINTRAGEN
# ==========================================
with tab_eintragen:
    st.header("🎯 Spiel eintragen")
    
    if aktueller_user != "Gast / Zuschauer":
        st.caption(f"Eingetragen von: **{aktueller_user}**")
        with st.container(border=True):
            spieltyp = st.selectbox(
                "📍 Spieltyp / Wertung wählen",
                ["🌳 Hobby / Park", "🏟️ Verein / Training", "🏆 Liga", "🥇 Turnier"],
                key="spieltyp_auswahl"
            )
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Team A (Dein Team)")
                team_a = st.multiselect("Spieler Team A", st.session_state.spieler, default=[aktueller_user], key="ta")
                punkte_a = st.number_input("Punkte Team A", min_value=0, max_value=13, value=0, step=1, key="pa")
            with col2:
                st.subheader("Team B (Gegner)")
                verfuegbar_b = [s for s in st.session_state.spieler if s not in team_a]
                team_b = st.multiselect("Spieler Team B", verfuegbar_b, key="tb")
                punkte_b = st.number_input("Punkte Team B", min_value=0, max_value=13, value=0, step=1, key="pb")

            if st.button("Spiel zur Bestätigung einsenden", type="primary", use_container_width=True):
                if aktueller_user not in team_a:
                    st.error("Du musst selbst in Team A mitspielen, um das Ergebnis einzutragen!")
                elif not team_a or not team_b:
                    st.error("Beide Teams müssen mindestens einen Spieler haben!")
                elif punkte_a == punkte_b:
                    st.error("Beim Petanque gibt es kein Unentschieden!")
                else:
                    jetzt = datetime.now().strftime("%d.%m.%Y %H:%M")
                    
                    st.session_state.warteschlange.append({
                        "Zeitstempel": jetzt,
                        "Spieltyp": spieltyp,
                        "Team A": team_a, "Punkte A": punkte_a,
                        "Team B": team_b, "Punkte B": punkte_b,
                        "EingetragenVon": aktueller_user
                    })
                    speichere_daten({"spieler": st.session_state.spieler, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                    st.success("Spiel eingereicht! Ein Spieler aus Team B muss es jetzt bestätigen.")
                    st.rerun()
    else:
        st.info("ℹ️ Wähle in der linken Seitenleiste dein Profil aus, um ein Spiel einzutragen.")


# ==========================================
# 5. TAB 3: OFFENE BESTÄTIGUNGEN
# ==========================================
with tab_offene:
    st.header("⏳ Offene Spielebestätigungen")
    
    offene_spiele = False
    for i in range(len(st.session_state.warteschlange) - 1, -1, -1):
        spiel = st.session_state.warteschlange[i]
        ta, tb = spiel["Team A"], spiel["Team B"]
        pa, pb = spiel["Punkte A"], spiel["Punkte B"]
        
        user_ist_gegner = aktueller_user in tb
        
        with st.container(border=True):
            st.write(f"**Typ:** {spiel['Spieltyp']} | 📅 {spiel['Zeitstempel']}")
            st.write(f"🤝 **{', '.join(ta)}** ({pa} : {pb}) **{', '.join(tb)}**")
            st.caption(f"Eingereicht von: {spiel['EingetragenVon']}")
            
            if user_ist_gegner or ist_admin:
                col_ja, col_nein = st.columns(2)
                with col_ja:
                    if st.button("✅ Bestätigen", key=f"ja_{i}", use_container_width=True):
                        st.session_state.spiele_historie.append(spiel)
                        st.session_state.warteschlange.pop(i)
                        speichere_daten({"spieler": st.session_state.spieler, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                        st.success("Spiel confirmed!")
                        st.rerun()
                with col_nein:
                    if st.button("❌ Ablehnen / Löschen", key=f"nein_{i}", use_container_width=True):
                        st.session_state.warteschlange.pop(i)
                        speichere_daten({"spieler": st.session_state.spieler, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                        st.warning("Spiel abgelehnt!")
                        st.rerun()
            else:
                st.warning("🔒 Warte auf Bestätigung durch einen Spieler aus Team B.")
            offene_spiele = True
            
    if not offene_spiele:
        st.write("Keine offenen Spiele zur Bestätigung.")