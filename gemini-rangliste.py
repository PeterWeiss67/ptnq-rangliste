import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

st.set_page_config(page_title="Petanque Elo-Rangliste", page_icon="🏆")

# --- DYNAMISCHER DATEN-SCHALTER ---
if st.config.get_option("server.headless"):
    DATEI_PFAD = "petanque_daten_PROD.json"
else:
    DATEI_PFAD = "petanque_daten_TEST.json"

ADMIN_PASSWORT = "petanque2026"
MASTER_PIN = "3011"  # 👈 RECHTE-SCHLÜSSEL: Ändere diese 4 Zahlen in deinen geheimen Admin-PIN!

# Sicherer Platzhalter, damit niemand ungefragt in alte Profile eindringen kann
START_PLATZHALTER_PIN = "PROFIL_SPERRE_INIT_2026"

# --- HILFSFUNKTION: NAMEN KÜRZEN ---
def kuerze_name(voller_name):
    teile = voller_name.strip().split()
    if len(teile) > 1:
        return f"{teile[0]} {teile[-1][0]}."
    return voller_name

def lade_daten():
    if os.path.exists(DATEI_PFAD):
        with open(DATEI_PFAD, "r", encoding="utf-8") as f:
            daten = json.load(f)
            if isinstance(daten.get("spieler"), list):
                daten["spieler"] = {s: {"pin": START_PLATZHALTER_PIN} for s in daten["spieler"]}
            if "warteschlange" not in daten:
                daten["warteschlange"] = []
            return daten
    return {
        "spieler": {},
        "spiele_historie": [],
        "warteschlange": []
    }

def speichere_daten(daten):
    with open(DATEI_PFAD, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)

gespeicherte_daten = lade_daten()

if 'spieler_dict' not in st.session_state:
    st.session_state.spieler_dict = gespeicherte_daten["spieler"]

if 'spiele_historie' not in st.session_state:
    st.session_state.spiele_historie = gespeicherte_daten["spiele_historie"]

if 'warteschlange' not in st.session_state:
    st.session_state.warteschlange = gespeicherte_daten["warteschlange"]

if 'aktueller_reiter' not in st.session_state:
    st.session_state.aktueller_reiter = "📊 Rangliste"
if 'dashboard_spieler' not in st.session_state:
    st.session_state.dashboard_spieler = None

liste_aller_spieler_namen = sorted(list(st.session_state.spieler_dict.keys()))


# --- SEITENLEISTE (LOGIN, REGISTRIERUNG & ADMIN) ---
with st.sidebar:
    if st.config.get_option("server.headless"):
        st.caption("🟢 Live-Modus (PROD)")
    else:
        st.caption("🟡 Test-Modus (LOCAL)")
        
    st.header("👤 Login")
    spieler_mappen = {kuerze_name(s): s for s in liste_aller_spieler_namen}
    gast_option = "Gast / Zuschauer"
    reg_option = "🆕 Neuer Spieler? Registrieren"
    auswahl_optionen = [gast_option, reg_option] + list(spieler_mappen.keys())
    
    user_kurz = st.selectbox("Wer bist du?", auswahl_optionen)
    
    user_eingeloggt = False
    aktueller_user = "Gast / Zuschauer"
    
    # --- FALL 1: SELBST-REGISTRIERUNG / AKTIVIERUNG ---
    if user_kurz == reg_option:
        st.subheader("📝 Profil erstellen / aktivieren")
        reg_name = st.text_input("Dein voller Name (z.B. Max Mustermann):", key="reg_name_input")
        reg_pin = st.text_input("Wähle einen 4-stelligen PIN (Nur Zahlen):", type="password", max_chars=4, key="reg_pin_input")
        
        if st.button("Konto aktivieren & Einloggen", type="primary", use_container_width=True):
            sauberer_name = reg_name.strip()
            if not sauberer_name:
                st.error("Bitte gib deinen Namen ein!")
            elif len(reg_pin) != 4 or not reg_pin.isdigit():
                st.error("Der PIN muss aus genau 4 Zahlen bestehen!")
            else:
                if sauberer_name in st.session_state.spieler_dict:
                    aktueller_status_pin = st.session_state.spieler_dict[sauberer_name].get("pin")
                    if aktueller_status_pin == START_PLATZHALTER_PIN:
                        st.session_state.spieler_dict[sauberer_name]["pin"] = reg_pin
                        speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                        st.success(f"🎉 Profil von '{kuerze_name(sauberer_name)}' erfolgreich aktiviert!")
                        st.rerun()
                    else:
                        st.error("Dieser Name ist bereits aktiv vergeben!")
                else:
                    st.session_state.spieler_dict[sauberer_name] = {"pin": reg_pin}
                    speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                    st.success(f"🎉 Willkommen, {kuerze_name(sauberer_name)}! Du wurdest neu registriert.")
                    st.rerun()

    # --- FALL 2: NORMALER LOGIN ---
    elif user_kurz != gast_option:
        gewaehlter_user = spieler_mappen[user_kurz]
        user_pin = st.text_input("Dein 4-stelliger PIN:", type="password", key="user_pin_input")
        korrekter_pin = st.session_state.spieler_dict[gewaehlter_user].get("pin", START_PLATZHALTER_PIN)
        
        if korrekter_pin == START_PLATZHALTER_PIN and user_pin != MASTER_PIN:
            st.warning("🔒 Profil nicht aktiviert. Bitte nutze oben 'Registrieren' mit exakt deinem Namen, um deinen PIN festzulegen!")
        elif user_pin == korrekter_pin or user_pin == MASTER_PIN:
            user_eingeloggt = True
            aktueller_user = gewaehlter_user
            st.success(f"🔓 Eingeloggt als {kuerze_name(aktueller_user)}")
        elif user_pin != "":
            st.error("❌ Falscher PIN!")
            
    st.divider()
    st.header("🔒 Admin-Bereich")
    pwd_eingabe = st.text_input("Passwort für Admin-Rechte:", type="password")
    ist_admin = (pwd_eingabe == ADMIN_PASSWORT)
    
    if ist_admin:
        st.success("🔓 Admin-Rechte aktiv!")
        
        st.subheader("👥 Spieler manuell hinzufügen")
        neuer_spieler = st.text_input("Voller Name:")
        if st.button("Spieler hinzufügen", use_container_width=True):
            spieler_name = neuer_spieler.strip()
            if spieler_name and spieler_name not in st.session_state.spieler_dict:
                st.session_state.spieler_dict[spieler_name] = {"pin": START_PLATZHALTER_PIN}
                speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                st.success(f"{kuerze_name(spieler_name)} hinzugefügt! (Wartet auf Aktivierung)")
                st.rerun()
                    
        st.subheader("📝 Spieler umbenennen")
        spieler_zu_aendern = st.selectbox("Welchen Namen ändern?", liste_aller_spieler_namen, format_func=kuerze_name)
        neuer_name = st.text_input("Neuer voller Name:")
        if st.button("Namen systemweit ändern", use_container_width=True):
            n_name = neuer_name.strip()
            if n_name and n_name != spieler_zu_aendern and n_name not in st.session_state.spieler_dict:
                st.session_state.spieler_dict[n_name] = st.session_state.spieler_dict.pop(spieler_zu_aendern)
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
                speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                st.success("Erfolgreich geändert!")
                st.rerun()


# ==========================================
# LOGO GANZ OBEN
# ==========================================
st.image("ptnq_logo.svg", use_container_width=True)
st.write("") 


# ==========================================
# INTERNE BERECHNUNG DER RANGLISTE (K=24 KONSTANT)
# ==========================================
rangliste = {s: {"Elo": 1000.0, "Spiele": 0, "Siege": 0, "Niederlagen": 0, "Differenz": 0, "Form": []} for s in liste_aller_spieler_namen}
K_FAKTOR = 24  # Standard Elo-Gewichtung für alle Spiele

for spiel in st.session_state.spiele_historie:
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
        df[["Platz", "Spieler", "Elo", "Spiele", "Differenz"]],
        use_container_width=True, 
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Platz": st.column_config.NumberColumn("🏆 Platz", format="%d"),
            "Spieler": st.column_config.TextColumn("👤 Spieler"),
            "Elo": st.column_config.NumberColumn("Elo-Punkte", format="%.1f 🔥"),
            "Spiele": st.column_config.NumberColumn("⚔️ Spiele", format="%d"),
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
                "Spiel-Nr.": i + 1, 
                "Team A": ", ".join([kuerze_name(x) for x in s["Team A"]]), 
                "Ergebnis": f"{s['Punkte A']} : {s['Punkte B']}", 
                "Team B": ", ".join([kuerze_name(x) for x in s["Team B"]]),
                "Datum/Zeit": s.get("Zeitstempel", "-")
            } for i, s in enumerate(st.session_state.spiele_historie)]
            st.table(schoene_historie)


# --- REITER 2: SPIELER-DASHBOARD ---
elif st.session_state.aktueller_reiter == "👤 Spieler-Details":
    st.header("👤 Spieler-Statistiken")
    
    # 1. PIN-ÄNDERUNG (Streng geschützt: Nur für das EIGENE, aktuell eingeloggte Profil)
    if user_eingeloggt:
        with st.expander(f"🔑 Mein Sicherheits-PIN ({kuerze_name(aktueller_user)}) ändern"):
            neuer_pin_eingabe = st.text_input("Neuer 4-stelliger PIN (nur Zahlen):", type="password", max_chars=4, key="pwd_user_change")
            if st.button("Meinen PIN dauerhaft speichern", use_container_width=True, key="btn_user_change"):
                if len(neuer_pin_eingabe) == 4 and neuer_pin_eingabe.isdigit():
                    st.session_state.spieler_dict[aktueller_user]["pin"] = neuer_pin_eingabe
                    speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                    st.success("🔒 Dein PIN wurde erfolgreich geändert und geschützt!")
                    st.rerun()
                else:
                    st.error("Der PIN muss aus genau 4 ZIFFERN bestehen!")

    # 2. ADMIN REFRESH-FUNKTION (Falls jemand seinen PIN vergessen hat)
    if ist_admin:
        st.write("")
        with st.expander("🛠️ Admin-Werkzeug: Spieler-PIN zurücksetzen"):
            pin_vergessen_spieler = st.selectbox("Für welchen Spieler PIN überschreiben?", liste_aller_spieler_namen, format_func=kuerze_name, key="admin_pin_reset_select")
            admin_neuer_pin = st.text_input("Neuer Notfall-PIN (4 Zahlen):", type="password", max_chars=4, key="admin_pin_reset_input")
            if st.button("PIN als Admin überschreiben", use_container_width=True, type="secondary"):
                if len(admin_neuer_pin) == 4 and admin_neuer_pin.isdigit():
                    st.session_state.spieler_dict[pin_vergessen_spieler]["pin"] = admin_neuer_pin
                    speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                    st.success(f"Der PIN für {kuerze_name(pin_vergessen_spieler)} wurde vom Admin geändert!")
                    st.rerun()
                else:
                    st.error("Muss aus genau 4 Ziffern bestehen!")

    st.divider()

    # 3. STATISTIKEN-ANZEIGE (Völlig unabhängig vom Login für jeden einsehbar)
    if st.session_state.dashboard_spieler in liste_aller_spieler_namen:
        default_index = liste_aller_spieler_namen.index(st.session_state.dashboard_spieler)
    elif aktueller_user in liste_aller_spieler_namen:
        default_index = liste_aller_spieler_namen.index(aktueller_user)
    else:
        default_index = 0
        
    ausgewaehlter_spieler = st.selectbox(
        "Wähle einen Spieler für Details aus:", 
        liste_aller_spieler_namen, 
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
    
    if user_eingeloggt:
        st.caption(f"Eingetragen von: **{kuerze_name(aktueller_user)}**")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Team A (Dein Team)")
                team_a = st.multiselect("Spieler Team A", liste_aller_spieler_namen, default=[aktueller_user], format_func=kuerze_name, key="ta")
                punkte_a = st.number_input("Punkte Team A", min_value=0, max_value=13, value=0, step=1, key="pa")
            with col2:
                st.subheader("Team B (Gegner)")
                verfuegbar_b = [s for s in liste_aller_spieler_namen if s not in team_a]
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
                        "Team A": team_a, "Punkte A": punkte_a,
                        "Team B": team_b, "Punkte B": punkte_b,
                        "EingetragenVon": aktueller_user
                    })
                    speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                    st.success("Spiel eingereicht! Ein Spieler aus Team B muss es jetzt bestätigen.")
                    st.rerun()
    else:
        st.info("ℹ️ Bitte logge dich zuerst in der linken Seitenleiste mit deinem Namen und PIN ein, um ein Spiel einzutragen.")


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
            st.write(f"📅 {spiel['Zeitstempel']}")
            st.write(f"🤝 **{', '.join([kuerze_name(x) for x in ta])}** ({pa} : {pb}) **{', '.join([kuerze_name(x) for x in tb])}**")
            st.caption(f"Eingereicht von: {kuerze_name(spiel['EingetragenVon'])}")
            
            if user_ist_gegner or ist_admin:
                col_ja, col_nein = st.columns(2)
                with col_ja:
                    if st.button("✅ Bestätigen", key=f"ja_{i}", use_container_width=True):
                        st.session_state.spiele_historie.append(spiel)
                        st.session_state.warteschlange.pop(i)
                        speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                        st.success("Spiel bestätigt!")
                        st.rerun()
                with col_nein:
                    if st.button("❌ Ablehnen / Löschen", key=f"nein_{i}", use_container_width=True):
                        st.session_state.warteschlange.pop(i)
                        speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                        st.warning("Spiel abgelehnt!")
                        st.rerun()
            else:
                st.warning("🔒 Warte auf Bestätigung durch einen Spieler aus Team B.")
            offene_spiele = True
            
    if not offene_spiele:
        st.write("Keine offenen Spiele zur Bestätigung.")