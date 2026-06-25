import streamlit as st
import pandas as pd
from daten_manager import kuerze_name, speichere_daten

def zeige_profil(df, rangliste, liste_aller_spieler_namen, aktueller_user, user_eingeloggt, ist_admin):
    st.header("👤 Spieler-Profile")
    
    if st.session_state.dashboard_spieler in liste_aller_spieler_namen:
        default_index = liste_aller_spieler_namen.index(st.session_state.dashboard_spieler)
    elif user_eingeloggt and aktueller_user in liste_aller_spieler_namen:
        default_index = liste_aller_spieler_namen.index(aktueller_user)
    else:
        default_index = 0
        
    ausgewaehlter_spieler = st.selectbox("🔎 Profil durchstöbern:", liste_aller_spieler_namen, index=default_index, format_func=kuerze_name, key="dashboard_auswahl_box")
    st.session_state.dashboard_spieler = ausgewaehlter_spieler
    
    if ausgewaehlter_spieler:
        ist_eigenes_profil = (user_eingeloggt and ausgewaehlter_spieler == aktueller_user)
        st.subheader(f"Willkommen in deinem Profil, {kuerze_name(ausgewaehlter_spieler)}! 👋" if ist_eigenes_profil else f"Profil von {kuerze_name(ausgewaehlter_spieler)}")

        # --- NEU: Daten aus der Spieldatenbank auslesen ---
        spieler_profil_daten = st.session_state.spieler_dict.get(ausgewaehlter_spieler, {})
        ist_verein = spieler_profil_daten.get("ist_vereinsspieler", False)
        lizenz = spieler_profil_daten.get("lizenznummer", "")
        verein_name = spieler_profil_daten.get("verein", "").strip()

        # --- NEU: VISUELLE ANZEIGE DES STATUS (Öffentlich für alle sichtbar) ---
        if ist_verein:
            if verein_name:
                st.success(f"🏟️ **Vereinsspieler** | Verein: **{verein_name}**")
            else:
                st.success("🏟️ **Vereinsspieler** (Kein Verein eingetragen)")
        else:
            if verein_name:
                st.info(f"🌳 **Freizeitspieler** | Gruppe/Verein: **{verein_name}**")
            else:
                st.info("🌳 **Freizeitspieler**")

        # --- NEU: PRIVATE EINGABE (Nur im EIGENEN Profil sichtbar) ---
        if ist_eigenes_profil:
            with st.expander("📝 Mein Profil bearbeiten (Verein & Lizenz)"):
                neuer_status = st.checkbox("Ich bin aktiver Vereinsspieler", value=ist_verein)
                neuer_verein = st.text_input("Mein Verein / Meine Boule-Gruppe:", value=verein_name).strip()
                
                # Die Lizenznummer wird NUR dem echten Besitzer hier im Feld angezeigt
                neue_lizenz = st.text_input("Meine Lizenznummer (für andere unsichtbar):", value=lizenz).strip()
                
                if st.button("Profil-Details speichern", use_container_width=True, type="primary"):
                    st.session_state.spieler_dict[aktueller_user]["ist_vereinsspieler"] = neuer_status
                    st.session_state.spieler_dict[aktueller_user]["verein"] = neuer_verein
                    st.session_state.spieler_dict[aktueller_user]["lizenznummer"] = neue_lizenz
                    
                    speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                    st.toast("✅ Profil-Details erfolgreich aktualisiert!", icon="💾")
                    import time
                    time.sleep(0.5)
                    st.rerun()

        # --- AB HIER FOLGT DEIN BESTEHENDER CODE UNVERÄNDERT ---
        if ist_eigenes_profil:
            with st.expander("🔑 Meinen Sicherheits-PIN ändern"):
                neuer_pin_eingabe = st.text_input("Neuer 4-stelliger PIN (nur Zahlen):", type="password", max_chars=4, key="pwd_user_change")
                if st.button("Meinen PIN dauerhaft speichern", use_container_width=True):
                    if len(neuer_pin_eingabe) == 4 and neuer_pin_eingabe.isdigit():
                        st.session_state.spieler_dict[aktueller_user]["pin"] = neuer_pin_eingabe
                        speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                        st.success("🔒 Dein PIN wurde erfolgreich geändert!")
                        st.rerun()
                    else:
                        st.error("Der PIN muss aus genau 4 ZIFFERN bestehen!")

        if ist_admin:
            with st.expander("🛠️ Admin-Werkzeug: Spieler-PIN zurücksetzen"):
                admin_neuer_pin = st.text_input("Neuer Notfall-PIN (4 Zahlen):", type="password", max_chars=4, key="admin_pin_reset_input")
                if st.button("PIN als Admin überschreiben", use_container_width=True):
                    if len(admin_neuer_pin) == 4 and admin_neuer_pin.isdigit():
                        st.session_state.spieler_dict[ausgewaehlter_spieler]["pin"] = admin_neuer_pin
                        speichere_daten({"spieler": st.session_state.spieler_dict, "spiele_historie": st.session_state.spiele_historie, "warteschlange": st.session_state.warteschlange})
                        st.success("Der PIN wurde vom Admin überschrieben!")
                        st.rerun()

        spieler_daten = df[df["VollerName"] == ausgewaehlter_spieler].iloc[0]
        siege, spiele = spieler_daten["Siege"], spieler_daten["Spiele"]
        quote = (siege / spiele * 100) if spiele > 0 else 0.0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("🏆 Ranglisten-Platz", f"Platz {spieler_daten['Platz']}")
        m2.metric("🔥 ELO-Rating", f"{spieler_daten['Elo']} Pkt.")
        m3.metric("🎯 Siegquote", f"{quote:.1f} %")
        
        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Spiele Gesamt", f"{spiele}")
        col2.metric("Siege ✅", f"{siege}")
        col3.metric("Niederlagen ❌", f"{spieler_daten['Niederlagen']}")
        col4.metric("Kugeldifferenz", f"{int(spieler_daten['Differenz']):+d}" if int(spieler_daten['Differenz']) != 0 else "0")
        
        st.divider()
        st.subheader("📊 Team-Analysen")
        partner_liste, gegner_liste = [], []
        
        for spiel in st.session_state.spiele_historie:
            if ausgewaehlter_spieler in spiel["Team A"]:
                mein_team, gegner_team, ich_sieg = spiel["Team A"], spiel["Team B"], (spiel["Punkte A"] > spiel["Punkte B"])
            elif ausgewaehlter_spieler in spiel["Team B"]:
                mein_team, gegner_team, ich_sieg = spiel["Team B"], spiel["Team A"], (spiel["Punkte B"] > spiel["Punkte A"])
            else:
                continue
            for p in mein_team:
                if p != ausgewaehlter_spieler: partner_liste.append({"Name": p, "Sieg": ich_sieg})
            for g in gegner_team: gegner_liste.append({"Name": g, "Niederlage": not ich_sieg})
                
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**👥 Häufigste Mitspieler:**")
            if partner_liste:
                df_p = pd.DataFrame(partner_liste).groupby("Name").agg(Spiele=("Sieg", "count"), Siege=("Sieg", "sum")).reset_index().sort_values(by="Spiele", ascending=False).head(3)
                for _, row in df_p.iterrows(): st.write(f"• {kuerze_name(row['Name'])} ({row['Spiele']}x, {row['Siege']} W)")
            else: st.caption("Noch keine Team-Matches.")
        with c2:
            st.markdown("**⚔️ Häufigste Gegner:**")
            if gegner_liste:
                df_g = pd.DataFrame(gegner_liste).groupby("Name").agg(Spiele=("Niederlage", "count"), Niederlagen=("Niederlage", "sum")).reset_index().sort_values(by="Spiele", ascending=False).head(3)
                for _, row in df_g.iterrows(): st.write(f"• {kuerze_name(row['Name'])} ({row['Spiele']}x, {row['Niederlagen']} L)")
            else: st.caption("Noch keine Gegner.")

        st.divider()
        st.subheader("⏳ Aktuelle Form (Letzte 5)")
        alle_form = rangliste[ausgewaehlter_spieler]["Form"]
        if alle_form:
            l5 = alle_form[-5:]
            l5.reverse()
            st.subheader("   ".join(l5))
        else: st.info("Noch keine Spiele.")