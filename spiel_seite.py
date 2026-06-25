import streamlit as st
from datetime import datetime
from daten_manager import kuerze_name, speichere_daten

def zeige_eintragen(user_eingeloggt, ist_admin, aktueller_user, liste_aller_spieler_namen):
    st.header("🎯 Spiel eintragen")
    if user_eingeloggt or ist_admin:
        eintrager_name = aktueller_user if user_eingeloggt else "Admin (Zettel-Eingabe)"
        st.caption(f"Eingetragen von: **{kuerze_name(eintrager_name)}**")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Team A")
                default_ta = [aktueller_user] if (user_eingeloggt and aktueller_user in liste_aller_spieler_namen) else []
                team_a = st.multiselect("Spieler Team A", liste_aller_spieler_namen, default=default_ta, format_func=kuerze_name, key="ta")
                punkte_a = st.number_input("Punkte Team A", 0, 13, 0, 1, key="pa")
            with col2:
                st.subheader("Team B")
                team_b = st.multiselect("Spieler Team B", [s for s in liste_aller_spieler_namen if s not in team_a], format_func=kuerze_name, key="tb")
                punkte_b = st.number_input("Punkte Team B", 0, 13, 0, 1, key="pb")

            if st.button("Spiel zur Bestätigung einsenden", type="primary", use_container_width=True):
                if not ist_admin and aktueller_user not in team_a: st.error("Du musst selbst in Team A stehen!")
                elif not team_a or not team_b: st.error("Teams unvollständig!")
                elif punkte_a == punkte_b: st.error("Kein Unentschieden erlaubt!")
                else:
                    st.session_state.warteschlange.append({
                        "Zeitstempel": datetime.now().strftime("%d.%m.%Y %H:%M"),
                        "Team A": team_a, "Punkte A": punkte_a, "Team B": team_b, "Punkte B": punkte_b,
                        "EingetragenVon": "Admin" if ist_admin else aktueller_user
                    })
                    speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                    
                    # --- GEÄNDERT: Signalisiert das erfolgreiche Abschicken über ein Toast ---
                    if ist_admin:
                        st.toast("🚀 Spiel erfolgreich eingereicht! Du kannst es drüben direkt freigeben.", icon="🎯")
                    else:
                        st.toast("🚀 Spiel erfolgreich zur Bestätigung an Team B geschickt!", icon="📩")
                        
                    import time
                    time.sleep(1) # Gibt dem System 1 Sekunde Zeit, damit man die Meldung sieht
                    st.rerun()
    else: st.info("ℹ️ Bitte logge dich ein, um Spiele einzutragen.")

def zeige_bestaetigungen(aktueller_user, ist_admin):
    st.header("⏳ Offene Spielebestätigungen")
    offene = False
    for i in range(len(st.session_state.warteschlange) - 1, -1, -1):
        spiel = st.session_state.warteschlange[i]
        with st.container(border=True):
            st.write(f"📅 {spiel['Zeitstempel']}")
            st.write(f"🤝 **{', '.join([kuerze_name(x) for x in spiel['Team A']])}** ({spiel['Punkte A']}:{spiel['Punkte B']}) **{', '.join([kuerze_name(x) for x in spiel['Team B']])}**")
            if aktueller_user in spiel["Team B"] or ist_admin:
                cja, cnein = st.columns(2)
                with cja:
                    if st.button("✅ Bestätigen", key=f"ja_{i}", use_container_width=True):
                        st.session_state.spiele_historie.append(spiel)
                        st.session_state.warteschlange.pop(i)
                        speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                        st.rerun()
                with cnein:
                    if st.button("❌ Löschen", key=f"nein_{i}", use_container_width=True):
                        st.session_state.warteschlange.pop(i)
                        speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                        st.rerun()
            else: st.warning("🔒 Warte auf Bestätigung durch Team B.")
            offene = True
    if not offene: st.write("Keine offenen Spiele zur Bestätigung.")