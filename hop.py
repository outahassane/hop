import streamlit as st
import pandas as pd

# 1. Création de colonnes pour un affichage côte à côte
col1, col2 = st.columns(2)

# 2. Configuration du sélecteur de mois
liste_mois = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

with col1:
    # L'index 8 correspond à "Septembre" (la liste commence à 0)
    mois_choisi = st.selectbox("Mois", liste_mois, index=8)

# 3. Configuration du sélecteur d'année
with col2:
    # La valeur par défaut est fixée à 2026
    annee_choisie = st.number_input("Année", min_value=2024, max_value=2035, value=2026, step=1)

# 4. Bouton de génération et message de succès
if st.button("🚀 Générer le planning du mois"):
    st.success(f"Planning généré avec succès pour {mois_choisi} {annee_choisie} ! Les règles de repos ont été respectées.")
    
    # Intégrez ici votre logique de génération de planning
    # et l'affichage de votre DataFrame avec st.dataframe(...)
