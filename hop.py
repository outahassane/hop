import streamlit as st
import calendar
import pandas as pd
from fpdf import FPDF
import io

# ==========================================
# 1. CLASSE POUR LE FORMATAGE DU PDF
# ==========================================
class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, 'Hôpital Sharifa Marrakech', border=0, align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_font('helvetica', 'I', 12)
        self.cell(0, 10, 'Planning de Gardes du Service', border=0, align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

def generer_document_pdf(df_planning, df_stats, mois_nom, annee):
    pdf = PDF()
    pdf.add_page()
    
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, f'Mois : {mois_nom} {annee}', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    pdf.set_font('helvetica', 'B', 10)
    col_widths = [30, 80, 80]
    headers = ['Date', 'Garde de Jour (12h)', 'Garde de Nuit (12h)']
    
    for i in range(len(headers)):
        pdf.cell(col_widths[i], 10, headers[i], border=1, align='C')
    pdf.ln()
    
    pdf.set_font('helvetica', '', 10)
    for _, row in df_planning.iterrows():
        pdf.cell(col_widths[0], 10, str(row['Date']), border=1, align='C')
        pdf.cell(col_widths[1], 10, str(row['Garde de Jour (12h)']), border=1, align='C')
        pdf.cell(col_widths[2], 10, str(row['Garde de Nuit (12h)']), border=1, align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, 'Statistiques de répartition (Equité)', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    pdf.set_font('helvetica', 'B', 10)
    stat_widths = [60, 40, 40, 40]
    stat_headers = ['Médecin', 'Total Gardes', 'Jours', 'Nuits']
    
    for i in range(len(stat_headers)):
        pdf.cell(stat_widths[i], 10, stat_headers[i], border=1, align='C')
    pdf.ln()
    
    pdf.set_font('helvetica', '', 10)
    for _, row in df_stats.iterrows():
        pdf.cell(stat_widths[0], 10, str(row['Médecin']), border=1, align='C')
        pdf.cell(stat_widths[1], 10, str(row['Total Gardes']), border=1, align='C')
        pdf.cell(stat_widths[2], 10, str(row['Jours (12h)']), border=1, align='C')
        pdf.cell(stat_widths[3], 10, str(row['Nuits (12h)']), border=1, align='C', new_x="LMARGIN", new_y="NEXT")
        
    return bytes(pdf.output())

# ==========================================
# 2. LE MOTEUR LOGIQUE
# ==========================================
def generer_planning_flexible(annee, mois, medecins, historique, conges):
    liste_med = list(medecins)
    while len(liste_med) < 8:
        liste_med.append(f"Remplaçant (Creux {len(liste_med)})")

    disponibilites = {m: -10 for m in liste_med}
    
    compteur_total = {m: 0 for m in liste_med}
    compteur_jour = {m: 0 for m in liste_med}
    compteur_nuit = {m: 0 for m in liste_med}

    # Integration du vrai historique pour la récupération au 1er du mois
    for hist in historique:
        id_unite_jour = hist['jour_relatif'] * 2
        id_unite_nuit = id_unite_jour + 1
        if hist['jour'] in disponibilites:
            disponibilites[hist['jour']] = id_unite_jour + 3
        if hist['nuit'] in disponibilites:
            disponibilites[hist['nuit']] = id_unite_nuit + 4

    _, nbr_jours = calendar.monthrange(annee, mois)
    planning = []

    for jour_du_mois in range(1, nbr_jours + 1):
        id_unite_jour = (jour_du_mois - 1) * 2
        id_unite_nuit = id_unite_jour + 1

        def n_est_pas_en_conge(medecin):
            if "Remplaçant" in medecin:
                return True
            return jour_du_mois not in conges.get(medecin, [])

        # --- AFFECTATION GARDE DE JOUR ---
        candidats_jour = [m for m in liste_med if disponibilites[m] <= id_unite_jour and n_est_pas_en_conge(m)]
        candidats_jour.sort(key=lambda m: (1 if "Remplaçant" in m else 0, compteur_jour[m] - compteur_nuit[m], compteur_total[m]))
        
        medecin_jour = candidats_jour[0]
        if "Remplaçant" not in medecin_jour:
            compteur_total[medecin_jour] += 1
            compteur_jour[medecin_jour] += 1
            disponibilites[medecin_jour] = id_unite_jour + 3

        # --- AFFECTATION GARDE DE NUIT ---
        candidats_nuit = [m for m in liste_med if disponibilites[m] <= id_unite_nuit and m != medecin_jour and n_est_pas_en_conge(m)]
        candidats_nuit.sort(key=lambda m: (1 if "Remplaçant" in m else 0, compteur_nuit[m] - compteur_jour[m], compteur_total[m]))
        
        medecin_nuit = candidats_nuit[0]
        if "Remplaçant" not in medecin_nuit:
            compteur_total[medecin_nuit] += 1
            compteur_nuit[medecin_nuit] += 1
            disponibilites[medecin_nuit] = id_unite_nuit + 4

        planning.append({
            'Jour_int': jour_du_mois,
            'Date': f"{jour_du_mois:02d}/{mois:02d}/{annee}",
            'Garde de Jour (12h)': medecin_jour,
            'Garde de Nuit (12h)': medecin_nuit
        })

    return planning, compteur_total, compteur_jour, compteur_nuit


# ==========================================
# 3. L'INTERFACE WEB (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Gardes - Hôpital Sharifa", page_icon="🏥", layout="wide")

st.title("🏥 Générateur de Gardes - Hôpital Sharifa Marrakech")
st.markdown("Automatisation avec respect strict des repos et rotation équitable Jour/Nuit.")

col1, col2 = st.columns(2)

dictionnaire_mois = {
    "Janvier": 1, "Février": 2, "Mars": 3, "Avril": 4,
    "Mai": 5, "Juin": 6, "Juillet": 7, "Août": 8,
    "Septembre": 9, "Octobre": 10, "Novembre": 11, "Décembre": 12
}

with col1:
    nom_mois = st.selectbox("Sélectionnez le mois", list(dictionnaire_mois.keys()), index=8)
    mois_cible = dictionnaire_mois[nom_mois]

with col2:
    annee_cible = st.number_input("Année", min_value=2024, max_value=2035, value=2026, step=1)

_, nbr_jours_mois = calendar.monthrange(annee_cible, mois_cible)

st.divider()

st.subheader("👨‍⚕️ Gestion des Médecins")
noms_par_defaut = "Dr SAKINA, Dr ELARCH, Dr IMANE, Dr ITTO"
medecins_input = st.text_area("Équipe actuelle (séparés par des virgules) :", noms_par_defaut)
liste_medecins = [m.strip() for m in medecins_input.split(',') if m.strip() != ""]

# -- NOUVELLE SECTION : HISTORIQUE --
st.divider()
st.subheader("⏪ Historique du mois précédent (Important)")
st.info("Indiquez qui était de garde les deux derniers jours du mois précédent pour garantir qu'ils aient leur temps de récupération.")

options_historique = ["Personne / Remplaçant"] + liste_medecins
col_h1, col_h2 = st.columns(2)

with col_h1:
    st.markdown("**Avant-dernier jour (J-2)**")
    j2_jour = st.selectbox("Garde de Jour (J-2)", options_historique, index=0)
    j2_nuit = st.selectbox("Garde de Nuit (J-2)", options_historique, index=0)

with col_h2:
    st.markdown("**Dernier jour (J-1)**")
    j1_jour = st.selectbox("Garde de Jour (J-1)", options_historique, index=0)
    j1_nuit = st.selectbox("Garde de Nuit (J-1)", options_historique, index=0)

st.divider()

st.subheader("🌴 Congés et Absences (Optionnel)")
conges_dict = {}

with st.expander("Cliquez ici pour déclarer des congés sur ce mois"):
    jours_possibles = list(range(1, nbr_jours_mois + 1))
    
    for med in liste_medecins:
        jours_absents = st.multiselect(f"Jours d'absence pour {med} :", options=jours_possibles)
        if jours_absents:
            conges_dict[med] = jours_absents

st.divider()

if st.button("🚀 Générer le planning du mois", use_container_width=True, type="primary"):
    
    if len(liste_medecins) == 0:
        st.error("Vous devez renseigner au moins un médecin.")
    else:
        # Construction de l'historique réel à partir des champs de saisie
        historique_reel = []
        if j2_jour != "Personne / Remplaçant" or j2_nuit != "Personne / Remplaçant":
            historique_reel.append({'jour_relatif': -2, 'jour': j2_jour, 'nuit': j2_nuit})
        if j1_jour != "Personne / Remplaçant" or j1_nuit != "Personne / Remplaçant":
            historique_reel.append({'jour_relatif': -1, 'jour': j1_jour, 'nuit': j1_nuit})
        
        # Génération
        planning, c_total, c_jour, c_nuit = generer_planning_flexible(annee_cible, mois_cible, liste_medecins, historique_reel, conges_dict)
        
        # Préparation des DataFrames
        df = pd.DataFrame(planning)
        df_affichage = df.drop(columns=['Jour_int']) 
        
        stats_data = []
        for m in liste_medecins:
            if "Remplaçant" not in m:
                stats_data.append({
                    "Médecin": m,
                    "Total Gardes": c_total[m],
                    "Jours (12h)": c_jour[m],
                    "Nuits (12h)": c_nuit[m]
                })
        stats_df = pd.DataFrame(stats_data)
        
        st.success(f"Planning généré avec succès ! Les gardes de la fin du mois précédent ont bien été prises en compte.")
        st.dataframe(df_affichage, use_container_width=True, hide_index=True)
        
        st.markdown("### 📊 Répartition des gardes ce mois-ci")
        st.table(stats_df)
        
        pdf_bytes = generer_document_pdf(df_affichage, stats_df, nom_mois, annee_cible)
        
        st.download_button(
            label="📄 Télécharger le planning en PDF (Prêt à imprimer)",
            data=pdf_bytes,
            file_name=f"Planning_Sharifa_{nom_mois}_{annee_cible}.pdf",
            mime="application/pdf",
            type="primary"
        )
