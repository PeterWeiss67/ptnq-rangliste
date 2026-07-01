import streamlit as st
import daten_manager as dm
import profil_seite as ps
import spiel_seite as ss

st.set_page_config(page_title="Petanque Elo-Rangliste", page_icon="🏆")

# Dynamischen Pfad setzen
dm.setze_datei_pfad(st.config.get_option("server.headless"))
gespeicherte_daten = dm.lade_daten()

if 'spieler_dict' not in st.session_state: st.session_state.spieler_dict = gespeicherte_daten["spieler"]
if 'spiele_historie' not in st.session_state: st.session_state.spiele_historie = gespeicherte_daten["spiele_historie"]
if 'warteschlange' not in st.session_state: st.session_state.warteschlange = gespeicherte_daten["warteschlange"]
if 'aktueller_reiter' not in st.session_state: st.session_state.aktueller_reiter = "📊 Rangliste"
if 'dashboard_spieler' not in st.session_state: st.session_state.dashboard_spieler = None

dm.liste_aller_spieler_namen = sorted(list(st.session_state.spieler_dict.keys()))

# --- SEITENLEISTE ---
with st.sidebar:
    st.caption("🟢 Live-Modus (PROD)" if st.config.get_option("server.headless") else "🟡 Test-Modus (LOCAL)")
    st.header("👤 Login")
    spieler_mappen = {dm.kuerze_name(s): s for s in dm.liste_aller_spieler_namen}
    auswahl_optionen = ["Gast / Zuschauer", "🆕 Neuer Spieler? Registrieren"] + list(spieler_mappen.keys())
    user_kurz = st.selectbox("Wer bist du?", auswahl_optionen)
    
    user_eingeloggt, aktueller_user = False, "Gast / Zuschauer"
    
    if user_kurz == "🆕 Neuer Spieler? Registrieren":
        reg_name = st.text_input("Dein voller Name:", key="reg_name_input")
        reg_pin = st.text_input("Wähle einen 4-stelligen PIN:", type="password", max_chars=4, key="reg_pin_input")
        if st.button("Konto aktivieren & Einloggen", type="primary", use_container_width=True):
            s_name = reg_name.strip()
            if s_name and len(reg_pin) == 4 and reg_pin.isdigit():
                if s_name in st.session_state.spieler_dict and st.session_state.spieler_dict[s_name].get("pin") == dm.START_PLATZHALTER_PIN:
                    st.session_state.spieler_dict[s_name]["pin"] = reg_pin
                else: st.session_state.spieler_dict[s_name] = {"pin": reg_pin}
                dm.speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                st.rerun()
    elif user_kurz != "Gast / Zuschauer":
        gewaehlter_user = spieler_mappen[user_kurz]
        user_pin = st.text_input("Dein 4-stelliger PIN:", type="password", key="user_pin_input")
        korrekter_pin = st.session_state.spieler_dict[gewaehlter_user].get("pin", dm.START_PLATZHALTER_PIN)
        if user_pin == korrekter_pin or user_pin == dm.MASTER_PIN:
            user_eingeloggt, aktueller_user = True, gewaehlter_user
            st.success(f"🔓 Eingeloggt!")

    st.divider()
    st.header("🔒 Admin-Bereich")
    pwd_eingabe = st.text_input("Passwort für Admin-Rechte:", type="password")
    ist_admin = (pwd_eingabe == dm.ADMIN_PASSWORT)
    if ist_admin:
        st.success("🔓 Admin aktiv!")
        neuer_spieler = st.text_input("Neuer Spieler Name:")
        if st.button("Spieler hinzufügen", use_container_width=True) and neuer_spieler.strip():
            st.session_state.spieler_dict[neuer_spieler.strip()] = {"pin": dm.START_PLATZHALTER_PIN}
            dm.speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
            st.rerun()

# Dieser Code kommt in deinen Admin-Bereich (unter die Passwort-Abfrage)
st.subheader("📦 Daten-Backup für Supabase")

# Wir laden deine echten Daten über deinen bisherigen Datenmanager
aktuelle_daten = dm.lade_daten()  # Ersetze das falls dein Befehl anders heißt

# JSON-Daten in Text umwandeln
json_string = json.dumps(aktuelle_daten, indent=4, ensure_ascii=False)

# Einen Download-Button für dich erstellen
st.download_button(
    label="📥 Aktuelle ptnq_daten_PROD.json herunterladen",
    data=json_string,
    file_name="petanque_daten_PROD.json",
    mime="application/json"
)

st.divider()
st.caption("© 2026 PTNQ. Alle Rechte vorbehalten.")
st.caption("PTNQ™ ist eine eingetragene Marke.")

# --- LOGO ALS LINK (Vollständig repariert und sauber eingerückt) ---
try:
    with open("ptnq_logo.svg", "r", encoding="utf-8") as f:
        svg_inhalt = f.read()
    
    # Wir geben dem Logo-Container eine eindeutige ID ('mein-verein-logo')
    st.markdown(
        f'<div id="mein-verein-logo" style="width: 100%; text-align: center;"><a href="./" target="_self" style="display: block; width: 100%; text-decoration: none;"><div style="width: 100%; max-width: 100%; height: auto;">{svg_inhalt}</div></a></div>',
        unsafe_allow_html=True
    )
    
    # Das CSS spricht jetzt NUR NOCH Elemente innerhalb von '#mein-verein-logo' an!
    st.html(
        """
        <style>
            #mein-verein-logo > a > div > svg {
                width: 100% !important;
                height: auto !important;
            }
        </style>
        """
    )
except Exception:
    st.markdown('<a href="./" target="_self" style="font-weight:bold; text-align:center; display:block; text-decoration:none;">🎯 Zur Startseite</a>', unsafe_allow_html=True)

# Berechnung holen
df, rangliste = dm.berechne_rangliste(st.session_state.spiele_historie, dm.liste_aller_spieler_namen)

ausgewaehlter_reiter = st.radio("Nav", ["📊 Rangliste", "👤 Spieler-Details", "🎯 Spiel eintragen", "⏳ Offene Bestätigungen"], 
                                index=["📊 Rangliste", "👤 Spieler-Details", "🎯 Spiel eintragen", "⏳ Offene Bestätigungen"].index(st.session_state.aktueller_reiter), horizontal=True, label_visibility="collapsed")
st.session_state.aktueller_reiter = ausgewaehlter_reiter

if st.session_state.aktueller_reiter == "📊 Rangliste":
    st.header("Rangliste")
    with st.expander("ℹ️ Wie funktioniert die PTNQ-Rangliste?"):
        st.markdown("""
        Willkommen bei unserer PTNQ-Rangliste! Um die Platzierungen absolut fair zu gestalten, nutzen wir das **Elo-System**.
        * **Startwert:** Jeder startet mit **1000 Punkten**.
        * **Starke Gegner belohnen mehr:** Ein Sieg gegen ein höher platziertes Team bringt dir deutlich mehr Punkte als ein Sieg gegen Anfänger.
        * **Kaum Risiko gegen Profis:** Verlierst du gegen ein Top-Team, verlierst du nur minimal Punkte.
        * **Teamwertung:** Bei Doublette/Triplette zählt der Durchschnitt des Teams, die Punkte bekommt nach dem Match aber jeder Spieler voll.
        """)
    
    auswahl_event = st.dataframe(df[["Platz", "Spieler", "Elo", "Spiele", "Differenz"]], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
                                 column_config={"Platz": "🏆 Platz", "Spieler": "👤 Spieler", "Elo": "Elo-Punkte", "Spiele": "⚔️ Spiele", "Differenz": "± Kugeln"})
    if auswahl_event and auswahl_event.get("selection", {}).get("rows"):
        st.session_state.dashboard_spieler = df.iloc[auswahl_event["selection"]["rows"][0]]["VollerName"]
        st.session_state.aktueller_reiter = "👤 Spieler-Details"
        st.rerun()

elif st.session_state.aktueller_reiter == "👤 Spieler-Details":
    ps.zeige_profil(df, rangliste, dm.liste_aller_spieler_namen, aktueller_user, user_eingeloggt, ist_admin)
elif st.session_state.aktueller_reiter == "🎯 Spiel eintragen":
    ss.zeige_eintragen(user_eingeloggt, ist_admin, aktueller_user, dm.liste_aller_spieler_namen)
elif st.session_state.aktueller_reiter == "⏳ Offene Bestätigungen":
    ss.zeige_bestaetigungen(aktueller_user, ist_admin)