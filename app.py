# -*- coding: utf-8 -*-
"""
PALOMBA Group — Tableau de bord interactif & Autonome
Saisie en direct et stockage 100% sécurisé sur PostgreSQL.
"""
from __future__ import annotations
import datetime as dt
import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import psycopg2

# ───────────────────────── Identité visuelle ─────────────────────────
NAVY = "#182951"; NAVY2 = "#215E99"; GOLD = "#C9A84C"; GOLDL = "#F3E7C6"
CREAM = "#F8F4EE"; VERT = "#2E7D32"; ROUGE = "#B3261E"; AMBRE = "#A8710F"; GRIS = "#8A8A8A"

STATUTS_DEV = ["1 - Dossier Entrant", "2 - Visite", "3 - En Étude", "4 - Offre Émise",
               "5 - Offre Accepté", "6 - PUV", "7 - Acté / En projet", "8 - Abandonné"]
ETATS_PROSPECTION = ["Prospection", "Courrier envoyé", "Relance courrier",
                     "R1 tel ou physique", "Transmis en développement", "Abandon"]

st.set_page_config(page_title="PALOMBA Group — Tableau de bord", page_icon="🏛️", layout="wide")

# ───────────────────────── Sécurité Accès ─────────────────────────
PASSWORD_SOCIETE = "Palomba2026!"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Accès Sécurisé — PALOMBA Group")
    pwd = st.text_input("Mot de passe de la société :", type="password")
    if st.button("Se connecter"):
        if pwd == PASSWORD_SOCIETE:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect")
    st.stop()

# ───────────────────────── Connexion BDD PostgreSQL ─────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    return None

def init_db():
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        # Table pour la prospection terrain
        cur.execute("""
            CREATE TABLE IF NOT EXISTS prospection_pure (
                id SERIAL PRIMARY KEY,
                developpeur TEXT,
                date_saisie DATE,
                commune TEXT,
                adresse TEXT,
                proprietaire TEXT,
                etat TEXT,
                action_faite TEXT,
                marge_estimee NUMERIC DEFAULT 0,
                observation TEXT
            );
        """)
        # Table pour les objectifs de la direction
        cur.execute("""
            CREATE TABLE IF NOT EXISTS direction_kpi (
                id SERIAL PRIMARY KEY,
                exercice TEXT,
                objectif_ca NUMERIC DEFAULT 0,
                objectif_actes NUMERIC DEFAULT 0,
                objectif_partenaires NUMERIC DEFAULT 0
            );
        """)
        # Remplissage initial des objectifs si vide
        cur.execute("SELECT COUNT(*) FROM direction_kpi;")
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO direction_kpi (exercice, objectif_ca, objectif_actes, objectif_partenaires)
                VALUES ('2026', 400000, 10, 5);
            """)
        conn.commit()
        cur.close()
        conn.close()

init_db()

# Styles CSS personnalisés
st.markdown(f"""
<style>
  .stApp {{ background:#FDFBF7; }}
  .bandeau {{ background:{NAVY}; padding:22px 28px; border-bottom:3px solid {GOLD}; margin-bottom:18px; }}
  .bandeau h1 {{ color:{CREAM}; font-size:1.7rem; letter-spacing:.16em; text-transform:uppercase;
                 font-weight:300; margin:0; font-family:Georgia,serif; }}
  .bandeau span {{ color:{GOLD}; letter-spacing:.3em; text-transform:uppercase; font-size:.72rem; }}
  .section {{ background:{GOLDL}; color:{NAVY}; padding:7px 14px; font-weight:700;
              letter-spacing:.2em; text-transform:uppercase; font-size:.72rem; margin:22px 0 12px; }}
  div[data-testid="stMetric"] {{ background:#fff; border:1px solid #E8E4DE; border-top:2px solid {GOLD};
                                 padding:14px 16px; }}
  div[data-testid="stMetricValue"] {{ font-family:Georgia,serif; color:{NAVY}; font-size:1.6rem; }}
  div[data-testid="stMetricLabel"] {{ text-transform:uppercase; letter-spacing:.14em;
                                      font-size:.62rem; color:{GRIS}; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="bandeau">
    <h1>Palomba Group</h1>
    <span>Système de Suivi & Pilotage Intégral</span>
</div>
""", unsafe_allow_html=True)

def euro(v: float) -> str:
    return f"{v:,.0f} €".replace(",", " ")

# ───────────────────────── Extraction des données ─────────────────────────
conn = get_db_connection()
df_live = pd.read_sql_query("SELECT * FROM prospection_pure ORDER BY id DESC", conn)
df_kpi = pd.read_sql_query("SELECT * FROM direction_kpi ORDER BY id DESC LIMIT 1", conn)
conn.close()

kpi_data = df_kpi.iloc[0] if not df_kpi.empty else {"exercice": "2026", "objectif_ca": 400000, "objectif_actes": 10, "objectif_partenaires": 5}

# ───────────────────────── Onglets Applicatifs ─────────────────────────
tab_kpi, tab_saisie, tab_admin = st.tabs(["📊 Direction & KPI", "✍️ Saisie Prospecteurs", "⚙️ Configuration Direction"])

# --- ONGLET 1 : GRAPHES ET KPI ---
with tab_kpi:
    st.markdown('<div class="section">Indicateurs Généraux de Performance</div>', unsafe_allow_html=True)
    
    # KPIs Financiers
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Objectif CA ({kpi_data['exercice']})", euro(float(kpi_data['objectif_ca'])))
    
    total_marge_pipe = df_live['marge_estimee'].sum() if not df_live.empty else 0.0
    c2.metric("Marge Totale Détectée", euro(total_marge_pipe), delta="Pipeline")
    c3.metric("Objectif Partenaires", f"{kpi_data['objectif_partenaires']}")
    
    st.markdown('<div class="section">Analyse Graphique de la Prospection</div>', unsafe_allow_html=True)
    if not df_live.empty:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            # Graphique d'activité par développeur
            count_dev = df_live['developpeur'].value_counts()
            fig_dev = go.Figure([go.Bar(x=count_dev.index, y=count_dev.values, marker_color=NAVY)])
            fig_dev.update_layout(title="Nombre de dossiers par Développeur", height=300)
            st.plotly_chart(fig_dev, use_container_width=True)
        with col_g2:
            # Répartition par état
            count_etat = df_live['etat'].value_counts()
            fig_etat = go.Figure([go.Bar(x=count_etat.index, y=count_etat.values, marker_color=GOLD)])
            fig_etat.update_layout(title="Répartition par État d'avancement", height=300)
            st.plotly_chart(fig_etat, use_container_width=True)
            
        st.markdown('<div class="section">Registre Central des Fiches Actives</div>', unsafe_allow_html=True)
        st.dataframe(df_live[['developpeur', 'date_saisie', 'commune', 'adresse', 'proprietaire', 'etat', 'marge_estimee', 'action_faite']], use_container_width=True)
    else:
        st.info("Aucune donnée disponible. Les graphiques s'afficheront dès qu'une fiche sera créée.")

# --- ONGLET 2 : SAISIE TERRAIN ---
with tab_saisie:
    st.markdown('<div class="section">Créer une nouvelle fiche de prospection</div>', unsafe_allow_html=True)
    with st.form("form_prospection_pure", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            dev_select = st.selectbox("Développeur référent", ["AP", "LP", "JMP"])
            commune = st.text_input("Commune *")
            adresse = st.text_input("Adresse / Localisation")
            proprio = st.text_input("Identité Propriétaire / Contact")
        with col2:
            etat_select = st.selectbox("État du dossier", ETATS_PROSPECTION)
            marge = st.number_input("Marge Estimée Palomba Group (€)", min_value=0, value=0, step=5000)
            action = st.text_input("Dernière action menée")
        obs = st.text_area("Observations / Historique ou commentaires libres")
        
        btn = st.form_submit_button("💾 Enregistrer dans le registre Cloud")
        if btn:
            if not commune:
                st.error("Le champ 'Commune' est obligatoire pour enregistrer une fiche.")
            else:
                conn = get_db_connection()
                if conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO prospection_pure (developpeur, date_saisie, commune, adresse, proprietaire, etat, action_faite, marge_estimee, observation)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (dev_select, dt.date.today(), commune, adresse, proprio, etat_select, action, marge, obs))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("🎉 Fiche enregistrée instantanément dans la base sécurisée ! Rechargez la page pour actualiser les graphiques.")

# --- ONGLET 3 : CONFIGURATION DIRECTION ---
with tab_admin:
    st.markdown('<div class="section">Mettre à jour les objectifs de l\'entreprise</div>', unsafe_allow_html=True)
    with st.form("form_admin"):
        ex = st.text_input("Exercice budgétaire", value=str(kpi_data['exercice']))
        obj_ca = st.number_input("Objectif annuel de Chiffre d'Affaires (€)", value=int(kpi_data['objectif_ca']), step=10000)
        obj_part = st.number_input("Objectif du nombre de Partenaires", value=int(kpi_data['objectif_partenaires']), step=1)
        
        btn_admin = st.form_submit_button("⚙️ Actualiser les Objectifs Officiels")
        if btn_admin:
            conn = get_db_connection()
            if conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO direction_kpi (exercice, objectif_ca, objectif_partenaires)
                    VALUES (%s, %s, %s)
                """, (ex, obj_ca, obj_part))
                conn.commit()
                cur.close()
                conn.close()
