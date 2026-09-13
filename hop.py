import streamlit as st
import calendar
import pandas as pd
from fpdf import FPDF
import datetime

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
        liste_med.append(f"RENFORT_VIRTUEL_{len(liste_med)}")

    disponibilites = {m: -10 for m in liste_med}
    
    compteur_total = {m: 0 for m in liste_med}
    compteur_jour = {m: 0 for m in liste_med}
    compteur_nuit = {m: 0 for m in liste_med}

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
            if "RENFORT" in medecin:
                return True
            return jour_du_mois not in conges.get(medecin, [])

        # --- AFFECTATION GARDE DE JOUR ---
        candidats_jour = [m for m in liste_med if disponibilites[m] <= id_unite_jour and n_est_pas_en_conge(m)]
        candidats_jour.sort(key=lambda m: (1 if "RENFORT" in m else 0, compteur_jour[m] - compteur_nuit[m], compteur_total[m]))
        
        medecin_jour = candidats_jour[0]
        if "RENFORT" not in medecin_jour:
            compteur_total[medecin_jour] += 1
            compteur_jour[medecin_jour] += 1
            disponibilites[medecin_jour] = id_unite_jour + 3

        # --- AFFECTATION GARDE DE NUIT ---
        candidats_nuit = [m for m in liste_med if disponibilites[m] <= id_unite_nuit and m != medecin_jour and n_est_pas_en_conge(m)]
        candidats_nuit.sort(key=lambda m: (1 if "RENFORT" in m else 0, compteur_nuit[m] - compteur_jour[m], compteur_total[m]))
        
        medecin_nuit = candidats_nuit[0]
        if "RENFORT" not in medecin_nuit:
            compteur_total[medecin_nuit] += 1
            compteur_nuit[medecin_nuit] += 1
            disponibilites[medecin_nuit] = id_unite_nuit + 4

        nom_affichage_jour = "Renfort / Garde Creuse" if "RENFORT" in medecin_jour else medecin_jour
        nom_affichage_nuit = "Renfort / Garde Creuse" if "RENFORT" in medecin_nuit else medecin_nuit

        planning.append({
            'Jour_int': jour_du_mois,
            'Date': f"{jour_du_mois:02d}/{mois:02d}/{annee}",
            'Garde de Jour (12h)': nom_affichage_jour,
            'Garde de Nuit (12h)': nom_affichage_nuit
        })

    return planning, compteur_total, compteur_jour, compteur_nuit


# ==========================================
# 3. L'INTERFACE WEB (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Gardes - Hôpital Sharifa", page_icon="🏥", layout="wide")

st.title("🏥 Générateur de Gardes - Hôpital Sharifa")
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

# -- GESTION DES MÉDECINS --
st.subheader("👨‍⚕️ Gestion des Médecins")

if "liste_medecins" not in st.session_state:
    st.session_state.liste_medecins = ["Dr SAKINA", "Dr ELARCH", "Dr IMANE", "Dr ITTO"]

col_ajout1, col_ajout2 = st.columns([3, 1])
with col_ajout1:
    nouveau_med = st.text_input("Nom du nouveau médecin", placeholder="Ex: Dr OMAR", label_visibility="collapsed")
with col_ajout2:
    if st.button("➕ Ajouter médecin", use_container_width=True):
        if nouveau_med and nouveau_med.strip() not in st.session_state.liste_medecins:
            st.session_state.liste_medecins.append(nouveau_med.strip())
            st.rerun()

st.markdown("**Équipe actuelle :**")
for i, med in enumerate(st.session_state.liste_medecins):
    col_nom, col_btn = st.columns([3, 1])
    with col_nom:
        st.markdown(f"🩺 **{med}**")
    with col_btn:
        if st.button("❌ Supprimer", key=f"del_{i}", use_container_width=True):
            st.session_state.liste_medecins.pop(i)
            st.rerun()

st.divider()

# -- HISTORIQUE DU MOIS PRÉCÉDENT --
st.subheader("⏪ Historique du mois précédent")

premier_jour_mois_cible = datetime.date(annee_cible, mois_cible, 1)
date_j1 = premier_jour_mois_cible - datetime.timedelta(days=1)
date_j2 = premier_jour_mois_cible - datetime.timedelta(days=2)
noms_mois_fr = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
label_j2 = f"Le {date_j2.day} {noms_mois_fr[date_j2.month]}"
label_j1 = f"Le {date_j1.day} {noms_mois_fr[date_j1.month]}"

options_historique = ["Personne / Renfort"] + st.session_state.liste_medecins
col_h1, col_h2 = st.columns(2)

with col_h1:
    st.markdown(f"**{label_j2} (Avant-dernier jour)**")
    j2_jour = st.selectbox("Garde de Jour", options_historique, key="j2_jour")
    j2_nuit = st.selectbox("Garde de Nuit", options_historique, key="j2_nuit")

with col_h2:
    st.markdown(f"**{label_j1} (Dernier jour)**")
    j1_jour = st.selectbox("Garde de Jour", options_historique, key="j1_jour")
    j1_nuit = st.selectbox("Garde de Nuit", options_historique, key="j1_nuit")

st.divider()

# -- GESTION DES CONGÉS (NOUVELLE INTERFACE) --
st.subheader("🌴 Congés et Absences (Optionnel)")

if "liste_conges" not in st.session_state:
    st.session_state.liste_conges = []

premier_jour = datetime.date(annee_cible, mois_cible, 1)
dernier_jour = datetime.date(annee_cible, mois_cible, nbr_jours_mois)

st.markdown("**Ajouter une période d'absence :**")
col_c1, col_c2, col_c3, col_c4 = st.columns([2, 1.5, 1.5, 1])

with col_c1:
    med_conge = st.selectbox("Médecin", st.session_state.liste_medecins, key="sel_med_conge")
with col_c2:
    debut_conge = st.date_input("Date de début", value=premier_jour, min_value=premier_jour, max_value=dernier_jour)
with col_c3:
    fin_conge = st.date_input("Date de fin", value=debut_conge, min_value=debut_conge, max_value=dernier_jour)
with col_c4:
    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
    if st.button("➕ Ajouter congé", key="btn_add_conge", use_container_width=True):
        st.session_state.liste_conges.append({
            "medecin": med_conge,
            "debut": debut_conge,
            "fin": fin_conge
        })
        st.rerun()

if st.session_state.liste_conges:
    st.markdown("**Absences enregistrées :**")
    for i, conge in enumerate(st.session_state.liste_conges):
        col_cn1, col_cn2 = st.columns([4, 1])
        with col_cn1:
            st.info(f"🏖️ **{conge['medecin']}** : du {conge['debut'].strftime('%d/%m/%Y')} au {conge['fin'].strftime('%d/%m/%Y')}")
        with col_cn2:
            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
            if st.button("❌ Retirer", key=f"del_conge_{i}", use_container_width=True):
                st.session_state.liste_conges.pop(i)
                st.rerun()

st.divider()

# -- SECTION : GÉNÉRATION --
if st.button("🚀 Générer le planning du mois", use_container_width=True, type="primary"):
    
    if len(st.session_state.liste_medecins) == 0:
        st.error("Vous devez renseigner au moins un médecin dans l'équipe.")
    else:
        # Traitement de l'historique
        historique_reel = []
        if j2_jour != "Personne / Renfort" or j2_nuit != "Personne / Renfort":
            historique_reel.append({'jour_relatif': -2, 'jour': j2_jour, 'nuit': j2_nuit})
        if j1_jour != "Personne / Renfort" or j1_nuit != "Personne / Renfort":
            historique_reel.append({'jour_relatif': -1, 'jour': j1_jour, 'nuit': j1_nuit})
        
        # Traitement des congés (transformation en dictionnaire)
        conges_dict = {}
        for c in st.session_state.liste_conges:
            med = c["medecin"]
            jours_conge = list(range(c["debut"].day, c["fin"].day + 1))
            if med in conges_dict:
                conges_dict[med].extend(jours_conge)
            else:
                conges_dict[med] = jours_conge
        
        planning, c_total, c_jour, c_nuit = generer_planning_flexible(
            annee_cible, mois_cible, st.session_state.liste_medecins, historique_reel, conges_dict
        )
        
        df = pd.DataFrame(planning)
        df_affichage = df.drop(columns=['Jour_int']) 
        
        stats_data = []
        for m in st.session_state.liste_medecins:
            if "RENFORT" not in m: 
                stats_data.append({
                    "Médecin": m,
                    "Total Gardes": c_total[m],
                    "Jours (12h)": c_jour[m],
                    "Nuits (12h)": c_nuit[m]
                })
        stats_df = pd.DataFrame(stats_data)
        
        st.success(f"Planning généré avec succès !")
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
