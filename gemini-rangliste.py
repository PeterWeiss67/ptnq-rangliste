import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# Die App bleibt für große Monitore zentriert
st.set_page_config(page_title="Petanque Elo-Rangliste", page_icon="🏆")

# --- DYNAMISCHER DATEN-SCHALTER ---
if st.config.get_option("server.headless"):
    DATEI_PFAD = "petanque_daten_PROD.json"
else:
    DATEI_PFAD = "petanque_daten_TEST.json"

ADMIN_PASSWORT = "petanque2026"

# --- HILFSFUNKTION: NAMEN KÜRZEN ---
def kuerze_name(voller_name):
    """Macht aus 'Max Mustermann' -> 'Max M.' und lässt 'Ali' -> 'Ali'"""
    teile = voller_name.strip().split()
    if len(teile) > 1:
        return f"{teile[0]} {teile[-1][0]}."
    return voller_name

def lade_daten():
    if os.path.exists(DATEI_PFAD):
        with open(DATEI_PFAD, "r", encoding="utf-8") as f:
            daten = json.load(f)
            if "warteschlange" not in daten:
                daten["warteschlange"] = []
            return daten
    return {"spieler": ["Ali", "Beatrix Name", "Charly Müller"], "spiele_historie": [], "warteschlange": []}

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

if 'aktueller_reiter' not in st.session_state:
    st.session_state.aktueller_reiter = "📊 Rangliste"
if 'dashboard_spieler' not in st.session_state:
    st.session_state.dashboard_spieler = None


# --- SEITENLEISTE ---
with st.sidebar:
    if st.config.get_option("server.headless"):
        st.caption("🟢 Live-Modus (PROD)")
    else:
        st.caption("🟡 Test-Modus (LOCAL)")
        
    st.header("👤 Mein Profil")
    # In der Auswahl zeigen wir die Kurznamen, merken uns aber den vollen Namen!
    spieler_mappen = {kuerze_name(s): s for s in st.session_state.spieler}
    gast_option = "Gast / Zuschauer"
    auswahl_optionen = [gast_option] + list(spieler_mappen.keys())
    
    user_kurz = st.selectbox("Wer bist du?", auswahl_optionen)
    aktueller_user = spieler_mappen.get(user_kurz, gast_option)
    
    st.divider()
    st.header("🔒 Admin-Bereich")
    pwd_eingabe = st.text_input("Passwort für Admin-Rechte:", type="password")
    ist_admin = (pwd_eingabe == ADMIN_PASSWORT)
    
    if ist_admin:
        st.success("🔓 Admin-Rechte active!")
        
        st.subheader("👥 Spieler hinzufügen")
        neuer_spieler = st.text_input("Voller Name (z.B. Max Mustermann):")
        if st.button("Spieler hinzufügen", use_container_width=True):
            spieler_name = neuer_spieler.strip()
            if spieler_name:
                if spieler_name not in st.session_state.spieler:
                    st.session_state.spieler.append(spieler_name)
                    st.session_state.spieler.sort()
                    speichere_daten({"spieler": st.session_state.spieler, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                    st.success(f"{kuerze_name(spieler_name)} hinzugefügt!")
                    st.rerun()
                    
        st.subheader("📝 Spieler umbenennen")
        spieler_zu_aendern = st.selectbox("Welchen Namen ändern?", st.session_state.spieler, format_func=kuerze_name)
        neuer_name = st.text_input("Neuer voller Name:")
        if st.button("Namen systemweit ändern", use_container_width=True):
            n_name = neuer_name.strip()
            if n_name and n_name != spieler_zu_aendern:
                if n_name in st.session_state.spieler:
                    st.error("Dieser Name existiert bereits!")
                else:
                    idx = st.session_state.spieler.index(spieler_zu_aendern)
                    st.session_state.spieler[idx] = n_name
                    st.session_state.spieler.sort()
                    
                    for spiel in st.session_state.spiele_historie:
                        spiel["Team A"] = [n_name if s == spieler_zu_aendern else s for s in spiel["Team A"]]
                        spiel["Team B"] = [n_name if s == spieler_zu_aendern else s for s in spiel["Team B"]]
                        if spiel.get("EingetragenVon") == spieler_zu_aendern: spiel["EingetragenVon"] = n_name
                            
                    for spiel in st.session_state.warteschlange:
                        spiel["Team A"] = [n_name if s == spieler_zu_aendern else s for s in spiel["Team A"]]
                        spiel["Team B"] = [n_name if s == spieler_zu_aendern else s for s in spiel["Team B"]]
                        if spiel.get("EingetragenVon") == spieler_zu_aendern: spiel["EingetragenVon"] = n_name
                    
                    if st.session_state.get("dashboard_spieler") == spieler_zu_aendern:
                        st.session_state.dashboard_spieler = n_name
                        
                    speichere_daten({"spieler": st.session_state.spieler, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                    st.success("Erfolgreich geändert!")
                    st.rerun()


# ==========================================
# LOGO GANZ OBEN
# ==========================================
st.image("ptnq_logo.svg", use_container_width=True)
st.write("") 


# ==========================================
# INTERNE BERECHNUNG DER RANGLISTE
# ==========================================
rangliste = {s: {"Elo": 1000.0, "Spiele": 0, "Siege": 0, "Niederlagen": 0, "Differenz": 0, "Form": []} for s in st.session_state.spieler}

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
df["Elo"] = df["Elo"].round(1)
df = df.sort_values(by=["Elo", "Differenz"], ascending=[False, False])
df.index.name = "VollerName"
df = df.reset_index()

df["Spieler"] = df["VollerName"].apply(kuerze_name)
df.insert(0, "Platz", range(1, len(df) + 1))


# ==========================================
# NAVIGATION REITER
# ==========================================
ausgewaehlter_reiter = st.radio(
    "Navigation",
    ["📊 Rangliste", "👤 Spieler-Details", "🎯 Spiel eintragen", "⏳ Offene Bestätigungen"],
    index=["📊 Rangliste", "👤 Spieler-Details", "🎯 Spiel eintragen", "⏳ Offene Bestätigungen"].index(st.session_state.aktueller_reiter),
    horizontal=True,
    label_visibility="collapsed"
)
st.session_state.aktueller_reiter = ausgewaehlter_reiter


# ==========================================
# REITER-LOGIK
# ==========================================

# --- REITER 1: RANGLISTE ---
if st.session_state.aktueller_reiter == "📊 Rangliste":
    st.header("Rangliste")
    st.caption("💡 Tippe einfach auf eine Zeile, um direkt zu den Spieler-Details zu springen.")

    auswahl_event = st.dataframe(
        df[["Platz", "Spieler", "Elo", "Differenz"]],
        use_container_width=True, 
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Platz": st.column_config.NumberColumn("🏆 Platz", format="%d"),
            "Spieler": st.column_config.TextColumn("👤 Spieler"),
            "Elo": st.column_config.NumberColumn("Elo-Punkte", format="%.1f 🔥"),
            "Differenz": st.column_config.NumberColumn("± Kugeln")
        }
    )

    if auswahl_event and "rows" in auswahl_event.get("selection", {}):
        selected_rows = auswahl_event["selection"]["rows"]
        if selected_rows:
            gewaehlter_index = selected_rows[0]
            geklickter_spieler = df.iloc[gewaehlter_index]["VollerName"]
            st.session_state.dashboard_spieler = geklickter_spieler
            st.session_state.aktueller_reiter = "👤 Spieler-Details"
            st.rerun()

    st.divider()
    
    if st.session_state.spiele_historie:
        st.subheader("📄 Bestätigte Spiele-Historie")
        with st.expander("🔍 Alle bestätigten Spiele anzeigen"):
            schoene_historie = [{
                "Nr.": i + 1, 
                "Typ": s.get("Spieltyp", "🏟️ Training"), 
                "Team A": ", ".join([kuerze_name(x) for x in s["Team A"]]), 
                "Ergebnis": f"{s['Punkte A']} : {s['Punkte B']}", 
                "Team B": ", ".join([kuerze_name(x) for x in s["Team B"]])
            } for i, s in enumerate(st.session_state.spiele_historie)]
            st.table(schoene_historie)


# --- REITER 2: SPIELER-DASHBOARD ---
elif st.session_state.aktueller_reiter == "👤 Spieler-Details":
    st.header("👤 Spieler-Statistiken")
    
    if st.session_state.dashboard_spieler in st.session_state.spieler:
        default_index = st.session_state.spieler.index(st.session_state.dashboard_spieler)
    elif aktueller_user in st.session_state.spieler:
        default_index = st.session_state.spieler.index(aktueller_user)
    else:
        default_index = 0
        
    ausgewaehlter_spieler = st.selectbox(
        "Wähle einen Spieler für Details aus:", 
        st.session_state.spieler, 
        index=default_index,
        format_func=kuerze_name,
        key="dashboard_auswahl_box"
    )
    st.session_state.dashboard_spieler = ausgewaehlter_spieler
    
    if ausgewaehlter_spieler:
        spieler_daten = df[df["VollerName"] == ausgewaehlter_spieler].iloc[0]
        siege, spiele = spieler_daten["Siege"], spieler_daten["Spiele"]
        quote = (siege / spiele * 100) if spiele > 0 else 0.0
        
        m1, m2, m3 = st.columns(3)
        m1.metric(label="🏆 Aktueller Rang", value=f"Platz {spieler_daten['Platz']}")
        m2.metric(label="🔥 Elo-Rating", value=f"{spieler_daten['Elo']} Pkt.")
        m3.metric(label="🎯 Siegquote", value=f"{quote:.1f} %")
        
        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Gesamtspiele", f"{spiele}")
        col2.metric("Siege 👍", f"{siege}")
        col3.metric("Niederlagen 👎", f"{spieler_daten['Niederlagen']}")
        diff_wert = int(spieler_daten['Differenz'])
        col4.metric("Kugeldifferenz", f"{diff_wert:+d}" if diff_wert != 0 else "0")
        
        st.subheader("⏳ Aktuelle Form (Letzte 5 Spiele)")
        alle_form_eintraege = rangliste[ausgewaehlter_spieler]["Form"]
        if alle_form_eintraege:
            letzte_5 = alle_form_eintraege[-5:]
            letzte_5.reverse()
            st.subheader("   ".join(letzte_5))
        else:
            st.info("Noch keine Spiele absolviert.")


# --- REITER 3: SPIEL EINTRAGEN ---
elif st.session_state.aktueller_reiter == "🎯 Spiel eintragen":
    st.header("🎯 Spiel eintragen")
    
    if aktueller_user != "Gast / Zuschauer":
        st.caption(f"Eingetragen von: **{kuerze_name(aktueller_user)}**")
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
                team_a = st.multiselect("Spieler Team A", st.session_state.spieler, default=[aktueller_user], format_func=kuerze_name, key="ta")
                punkte_a = st.number_input("Punkte Team A", min_value=0, max_value=13, value=0, step=1, key="pa")
            with col2:
                st.subheader("Team B (Gegner)")
                verfuegbar_b = [s for s in st.session_state.spieler if s not in team_a]
                team_b = st.multiselect("Spieler Team B", verfuegbar_b, format_func=kuerze_name, key="tb")
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


# --- REITER 4: OFFENE BESTÄTIGUNGEN ---
elif st.session_state.aktueller_reiter == "⏳ Offene Bestätigungen":
    st.header("⏳ Offene Spielebestätigungen")
    
    offene_spiele = False
    for i in range(len(st.session_state.warteschlange) - 1, -1, -1):
        spiel = st.session_state.warteschlange[i]
        ta, tb = spiel["Team A"], spiel["Team B"]
        pa, pb = spiel["Punkte A"], spiel["Punkte B"]
        
        user_ist_gegner = aktueller_user in tb
        
        with st.container(border=True):
            st.write(f"**Typ:** {spiel['Spieltyp']} | 📅 {spiel['Zeitstempel']}")
            st.write(f"🤝 **{', '.join([kuerze_name(x) for x in ta])}** ({pa} : {pb}) **{', '.join([kuerze_name(x) for x in tb])}**")
            st.caption(f"Eingereicht von: {kuerze_name(spiel['EingetragenVon'])}")
            
            if user_ist_gegner or ist_admin:
                col_ja, col_nein = st.columns(2)
                with col_ja:
                    if st.button("✅ Bestätigen", key=f"ja_{i}", use_container_width=True):
                        st.session_state.spiele_historie.append(spiel)
                        st.session_state.warteschlange.pop(i)
                        speichere_daten({"spieler": st.session_state.spieler, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                        st.success("Spiel bestätigt!")
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