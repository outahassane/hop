import streamlit as st
import calendar
import pandas as pd

# ==========================================
# 1. LE MOTEUR LOGIQUE (L'ALGORITHME)
# ==========================================
def generer_planning_flexible(annee, mois, medecins, historique, conges):
    # On s'assure d'avoir un bon stock de "Remplaçants" si beaucoup de médecins sont en congé
    liste_med = list(medecins)
    while len(liste_med) < 8:
        liste_med.append(f"Remplaçant (Creux {len(liste_med)})")

    disponibilites = {m: -10 for m in liste_med}
    compteur_gardes = {m: 0 for m in liste_med}

    # Traitement de l'historique (pour simplifier, désactivé si vide)
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

        # Fonction locale pour vérifier si le médecin est libre de tout congé ce jour-là
        def n_est_pas_en_conge(medecin):
            if "Remplaçant" in medecin:
                return True # Les remplaçants virtuels n'ont pas de congés
            return jour_du_mois not in conges.get(medecin, [])

        # --- AFFECTATION GARDE DE JOUR ---
        candidats_jour = [m for m in liste_med if disponibilites[m] <= id_unite_jour and n_est_pas_en_conge(m)]
        candidats_jour.sort(key=lambda m: (1 if "Remplaçant" in m else 0, compteur_gardes[m]))
        
        medecin_jour = candidats_jour[0]
        if "Remplaçant" not in medecin_jour:
            compteur_gardes[medecin_jour] += 1
            disponibilites[medecin_jour] = id_unite_jour + 3 # Repos 24h

        # --- AFFECTATION GARDE DE NUIT ---
        candidats_nuit = [m for m in liste_med if disponibilites[m] <= id_unite_nuit and m != medecin_jour and n_est_pas_en_conge(m)]
        candidats_nuit.sort(key=lambda m: (1 if "Remplaçant" in m else 0, compteur_gardes[m]))
        
        medecin_nuit = candidats_nuit[0]
        if "Remplaçant" not in medecin_nuit:
            compteur_gardes[medecin_nuit] += 1
            disponibilites[medecin_nuit] = id_unite_nuit + 4 # Repos 36h

        planning.append({
            'Jour': jour_du_mois,
            'Date': f"{jour_du_mois:02d}/{mois:02d}/{annee}",
            'Garde de Jour (12h)': medecin_jour,
            'Garde de Nuit (12h)': medecin_nuit
        })

    return planning, compteur_gardes


# ==========================================
# 2. L'INTERFACE WEB (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Gardes - Hôpital Sharifa", page_icon="🏥", layout="wide")

st.title("🏥 Générateur de Gardes - Hôpital Sharifa Marrakech")
st.markdown("Automatisation des plannings avec respect strict des repos (24h post-jour, 36h post-nuit).")

# -- SECTION 1 : Paramètres du mois --
col1, col2 = st.columns(2)
with col1:
    mois_cible = st.selectbox("Sélectionnez le mois", range(1, 13), index=0)
with col2:
    annee_cible = st.number_input("Année", value=2024, step=1)

_, nbr_jours_mois = calendar.monthrange(annee_cible, mois_cible)

st.divider()

# -- SECTION 2 : Gestion des Médecins --
st.subheader("👨‍⚕️ Gestion des Médecins")
st.info("Pour ajouter un médecin, ajoutez une virgule et son nom. Pour en supprimer un, effacez-le simplement de la liste.")

noms_par_defaut = "Dr SAKINA, Dr ELARCH, Dr IMANE, Dr ITTO"
medecins_input = st.text_area("Équipe actuelle :", noms_par_defaut)
liste_medecins = [m.strip() for m in medecins_input.split(',') if m.strip() != ""]

# -- SECTION 3 : Gestion des Congés --
st.subheader("🌴 Congés et Absences (Optionnel)")
conges_dict = {}

with st.expander("Cliquez ici pour déclarer des congés sur ce mois"):
    jours_possibles = list(range(1, nbr_jours_mois + 1))
    
    # Créer un sélecteur de jours pour chaque médecin existant
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
        # Historique vide pour simplifier dans cette version (on suppose que tout le monde est reposé au 1er du mois)
        historique_fictif = []
        
        # Génération
        planning, stats = generer_planning_flexible(annee_cible, mois_cible, liste_medecins, historique_fictif, conges_dict)
        
        # Conversion en tableau (DataFrame Pandas) pour un bel affichage
        df = pd.DataFrame(planning)
        df = df.drop(columns=['Jour']) # On cache la colonne technique
        
        st.success("Planning généré avec succès ! Les règles de repos ont été respectées.")
        
        # Affichage
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Statistiques d'équité
        st.markdown("### 📊 Répartition des gardes ce mois-ci")
        stats_df = pd.DataFrame(list(stats.items()), columns=["Médecin", "Nombre de gardes"])
        # On ne garde que les vrais médecins (on enlève les stats des remplaçants)
        stats_df = stats_df[~stats_df["Médecin"].str.contains("Remplaçant")]
        st.table(stats_df)
        
        # Bouton d'exportation Excel/CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger le planning pour Excel (CSV)",
            data=csv,
            file_name=f"Planning_Sharifa_{mois_cible}_{annee_cible}.csv",
            mime="text/csv"
        )
