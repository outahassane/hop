import streamlit as st
import calendar
import pandas as pd

# ==========================================
# 1. LE MOTEUR LOGIQUE (L'ALGORITHME ROTATIF)
# ==========================================
def generer_planning_flexible(annee, mois, medecins, historique, conges):
    liste_med = list(medecins)
    while len(liste_med) < 8:
        liste_med.append(f"Remplaçant (Creux {len(liste_med)})")

    disponibilites = {m: -10 for m in liste_med}
    
    # NOUVEAU : Compteurs séparés pour forcer l'équité et la rotation
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
            if "Remplaçant" in medecin:
                return True
            return jour_du_mois not in conges.get(medecin, [])

        # --- AFFECTATION GARDE DE JOUR ---
        candidats_jour = [m for m in liste_med if disponibilites[m] <= id_unite_jour and n_est_pas_en_conge(m)]
        # Tri : On priorise celui qui a fait le plus de nuits par rapport à ses jours (rotation), puis l'équité totale
        candidats_jour.sort(key=lambda m: (1 if "Remplaçant" in m else 0, compteur_jour[m] - compteur_nuit[m], compteur_total[m]))
        
        medecin_jour = candidats_jour[0]
        if "Remplaçant" not in medecin_jour:
            compteur_total[medecin_jour] += 1
            compteur_jour[medecin_jour] += 1
            disponibilites[medecin_jour] = id_unite_jour + 3 # Repos 24h

        # --- AFFECTATION GARDE DE NUIT ---
        candidats_nuit = [m for m in liste_med if disponibilites[m] <= id_unite_nuit and m != medecin_jour and n_est_pas_en_conge(m)]
        # Tri : On priorise celui qui a fait le plus de jours par rapport à ses nuits (rotation), puis l'équité totale
        candidats_nuit.sort(key=lambda m: (1 if "Remplaçant" in m else 0, compteur_nuit[m] - compteur_jour[m], compteur_total[m]))
        
        medecin_nuit = candidats_nuit[0]
        if "Remplaçant" not in medecin_nuit:
            compteur_total[medecin_nuit] += 1
            compteur_nuit[medecin_nuit] += 1
            disponibilites[medecin_nuit] = id_unite_nuit + 4 # Repos 36h

        planning.append({
            'Jour_int': jour_du_mois,
            'Date': f"{jour_du_mois:02d}/{mois:02d}/{annee}",
            'Garde de Jour (12h)': medecin_jour,
            'Garde de Nuit (12h)': medecin_nuit
        })

    return planning, compteur_total, compteur_jour, compteur_nuit


# ==========================================
# 2. L'INTERFACE WEB (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Gardes - Hôpital Sharifa", page_icon="🏥", layout="wide")

st.title("🏥 Générateur de Gardes - Hôpital Sharifa Marrakech")
st.markdown("Automatisation avec respect strict des repos et **rotation équitable Jour/Nuit**.")

# -- SECTION 1 : Paramètres --
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

# -- SECTION 2 : Gestion des Médecins --
st.subheader("👨‍⚕️ Gestion des Médecins")
st.info("Pour ajouter un médecin, ajoutez une virgule et son nom. Pour en supprimer un, effacez-le de la liste.")

noms_par_defaut = "Dr SAKINA, Dr ELARCH, Dr IMANE, Dr ITTO"
medecins_input = st.text_area("Équipe actuelle :", noms_par_defaut)
liste_medecins = [m.strip() for m in medecins_input.split(',') if m.strip() != ""]

# -- SECTION 3 : Gestion des Congés --
st.subheader("🌴 Congés et Absences (Optionnel)")
conges_dict = {}

with st.expander("Cliquez ici pour déclarer des congés sur ce mois"):
    jours_possibles = list(range(1, nbr_jours_mois + 1))
    
    for med in liste_medecins:
        jours_absents = st.multiselect(f"Jours d'absence pour {med} :", options=jours_possibles)
        if jours_absents:
            conges_dict[med] = jours_absents

st.divider()

# -- SECTION 4 : Génération et Affichage --
if st.button("🚀 Générer le planning du mois", use_container_width=True, type="primary"):
    
    if len(liste_medecins) == 0:
        st.error("Vous devez renseigner au moins un médecin.")
    else:
        historique_fictif = []
        
        # Lancement de l'algorithme
        planning, c_total, c_jour, c_nuit = generer_planning_flexible(annee_cible, mois_cible, liste_medecins, historique_fictif, conges_dict)
        
        df = pd.DataFrame(planning)
        df = df.drop(columns=['Jour_int']) 
        
        st.success(f"Planning généré avec succès pour {nom_mois} {annee_cible} ! Rotation Jour/Nuit respectée.")
        
        # Affichage du tableau de gardes
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Statistiques d'équité (Améliorées)
        st.markdown("### 📊 Répartition des gardes ce mois-ci")
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
        st.table(stats_df)
        
        # Bouton d'exportation CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger le planning pour Excel (CSV)",
            data=csv,
            file_name=f"Planning_Sharifa_{nom_mois}_{annee_cible}.csv",
            mime="text/csv"
        )
