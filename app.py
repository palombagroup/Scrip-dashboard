import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import datetime

# 1. CONFIGURATION DE LA PAGE ET SÉCURITÉ
st.set_page_config(page_title="PALOMBA Group - Dashboard", layout="wide", page_icon="🏢")

# Définition du mot de passe unique de la société
PASSWORD_SOCIETE = "Palomba2026!" # À modifier par le mot de passe de votre choix

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def check_password():
    if st.session_state["password_input"] == PASSWORD_SOCIETE:
        st.session_state["authenticated"] = True
        st.session_state["password_error"] = False
    else:
        st.session_state["password_error"] = True

# Écran de connexion
if not st.session_state["authenticated"]:
    st.title("🔒 Accès Sécurisé — PALOMBA Group")
    st.text_input("Veuillez entrer le mot de passe de la société :", type="password", key="password_input", on_change=check_password)
    if st.session_state.get("password_error"):
        st.error("Mot de passe incorrect. Veuillez réessayer.")
    st.stop()

# 2. CONNEXION À LA BASE DE DONNÉES POSTGRESQL (RENDER)
# Streamlit récupère automatiquement le lien secret de la base de données depuis Render
import os
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost:5432/postgres")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

# Création automatique de la table de prospection si elle n'existe pas
def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prospection (
            id SERIAL PRIMARY KEY,
            developpeur TEXT,
            date_creation DATE,
            commune TEXT,
            adresse TEXT,
            proprietaire TEXT,
            observation TEXT,
            etat TEXT,
            action_faite TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# 3. INTERFACE DU DASHBOARD
st.title("🏢 PALOMBA Group — Espace Collaboratif")
st.markdown("---")

tab1, tab2 = st.tabs(["✍️ Renseigner un nouveau contact", "📊 Visualisation des données"])

# ONGLET 1 : FORMULAIRE DE SAISIE POUR LES PROSPECTEURS
with tab1:
    st.subheader("📝 Formulaire de Prospection Terrain")
    st.markdown("Remplissez les champs ci-dessous pour ajouter une parcelle ou un contact au système.")
    
    with st.form("form_prospection", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            dev = col1.selectbox("Développeur", ["AP", "LP", "JMP"])
            commune = col1.text_input("Commune *")
            adresse = col1.text_input("Adresse précise")
        with col2:
            proprietaire = col2.text_input("Nom du Propriétaire / Structure")
            etat = col2.selectbox("État d'avancement", ["Prospection", "Courrier envoyé", "Relance courrier", "R1 obtenu", "Transmis en développement", "Abandon"])
        with col3:
            action = col3.text_input("Dernière action faite")
            obs = col3.text_area("Observations / Commentaires clés")
            
        submitted = st.form_submit_button("💾 Enregistrer dans la base de données")
        
        if submitted:
            if not commune:
                st.error("Le champ 'Commune' est obligatoire.")
            else:
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO prospection (developpeur, date_creation, commune, adresse, proprietaire, observation, etat, action_faite)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """, (dev, datetime.date.today(), commune, adresse, proprietaire, obs, etat, action))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("🎉 Données enregistrées avec succès et sécurisées !")
                except Exception as e:
                    st.error(f"Erreur lors de l'enregistrement : {e}")

# ONGLET 2 : VISUALISATION ET ANALYSE (Pour la direction)
with tab2:
    st.subheader("📋 Données en temps réel")
    
    # Récupération des données depuis PostgreSQL
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM prospection ORDER BY id DESC;", conn)
    conn.close()
    
    if df.empty:
        st.info("Aucune donnée n'a encore été saisie par les prospecteurs.")
    else:
        # Affichage des statistiques rapides
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        col_stat1.metric("Total Contacts", len(df))
        col_stat2.metric("En cours de Prospection", len(df[df["etat"] == "Prospection"]))
        col_stat3.metric("Transmis au Développement", len(df[df["etat"] == "Transmis en développement"]))
        
        st.markdown("---")
        
        # Tableau de données interactif
        st.write("### Registre complet")
        st.dataframe(df, use_container_width=True)
