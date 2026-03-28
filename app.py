import streamlit as st
import pandas as pd
import math
from pyairtable import Table

# --- CONFIGURATION ---
st.set_page_config(page_title="Cocktail Planner Pro", layout="centered")

# CSS Mobile First
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #FF4B4B; color: white; font-weight: bold; }
    .card { background-color: white; padding: 15px; border-radius: 12px; border-left: 6px solid #FF4B4B; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .ing-title { font-weight: bold; color: #2c3e50; font-size: 1.1em; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION AIRTABLE ---
try:
    api_key = st.secrets["airtable"]["api_key"]
    base_id = st.secrets["airtable"]["base_id"]
    
    # On définit les 4 tables
    t_recettes = Table(api_key, base_id, st.secrets["airtable"]["table_recettes"])
    t_ingredients = Table(api_key, base_id, st.secrets["airtable"]["table_ingredients"])
    t_commande = Table(api_key, base_id, st.secrets["airtable"]["table_commande"])
    t_courses = Table(api_key, base_id, st.secrets["airtable"]["table_listeDeCourses"])
except Exception as e:
    st.error("Erreur de configuration des secrets Airtable.")
    st.stop()

@st.cache_data(ttl=60)
def fetch_data(table_obj):
    data = table_obj.all()
    return pd.DataFrame([ {**r['fields'], 'id': r['id']} for r in data ])

# Chargement des données
df_recettes = fetch_data(t_recettes)
df_ingredients = fetch_data(t_ingredients)
df_commande = fetch_data(t_commande)
df_courses = fetch_data(t_courses)

# --- INTERFACE ---
st.title("🍸 Cocktail Manager")

# 1. Choix du Cocktail
if not df_recettes.empty:
    # On suppose que la colonne s'appelle 'Nom' dans ta table Recettes
    nom_col = 'Nom' if 'Nom' in df_recettes.columns else df_recettes.columns[0]
    choix_cocktail = st.selectbox("Sélectionnez un cocktail", df_recettes[nom_col].unique())
    
    # 2. Nombre de PAX
    pax = st.number_input("Nombre d'invités (PAX)", min_value=1, value=50)

    if st.button("GÉNÉRER LA LISTE DE COURSES"):
        st.divider()
        
        # Trouver l'ID du cocktail sélectionné
        id_cocktail = df_recettes[df_recettes[nom_col] == choix_cocktail]['id'].values[0]
        
        # Filtrer les ingrédients liés à ce cocktail
        # Dans Airtable, la colonne 'Recette' est une liste d'IDs
        mask = df_ingredients['Recettes'].apply(lambda x: id_cocktail in x if isinstance(x, list) else x == id_cocktail)
        ingredients_du_cocktail = df_ingredients[mask]

        if not ingredients_du_cocktail.empty:
            for _, ing in ingredients_du_cocktail.iterrows():
                nom_ing = ing.get('Nom', 'Ingrédient sans nom')
                qty_unitaire = ing.get('Quantité', 0)
                unite = ing.get('Unité', 'cl')
                total_besoin = qty_unitaire * pax
                
                # Affichage de la carte ingrédient
                st.markdown(f"""
                <div class="card">
                    <div class="ing-title">{nom_ing}</div>
                    <div>Besoin pour {pax} pers : <b>{total_besoin} {unite}</b></div>
                </div>
                """, unsafe_allow_html=True)
                
                # RECHERCHE DANS LA TABLE LISTE DE COURSES (STOCK/FORMATS)
                # On cherche les lignes qui correspondent au nom de l'ingrédient
                formats = df_courses[df_courses['Ingrédient'] == nom_ing]
                
                if not formats.empty:
                    cols = st.columns(len(formats))
                    for i, (_, f) in enumerate(formats.iterrows()):
                        try:
                            # Calcul du nombre de bouteilles
                            contenance = float(f.get('Contenance', 1))
                            nb_bout = math.ceil(total_besoin / contenance)
                            with cols[i]:
                                st.metric(label=f.get('Marque', 'Standard'), value=f"{nb_bout}")
                                st.caption(f"Format {contenance} {f.get('Unité', 'cl')}")
                        except:
                            continue
                else:
                    st.caption(f"ℹ️ Aucun format de bouteille configuré pour {nom_ing}")
        else:
            st.warning("Aucun ingrédient trouvé pour ce cocktail dans la table 'Ingrédients'.")
else:
    st.error("La table Recettes est vide.")