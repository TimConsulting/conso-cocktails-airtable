import streamlit as st
import pandas as pd
import math
from pyairtable import Table

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Cocktail Planner Pro", layout="centered")

# CSS pour une interface propre sur Mobile
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3.5em;
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
        border: none;
    }
    .card {
        background-color: white;
        padding: 15px;
        border-radius: 12px;
        border-left: 6px solid #FF4B4B;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .ing-title {
        font-weight: bold;
        color: #2c3e50;
        font-size: 1.1em;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

# --- RÉCUPÉRATION DES SECRETS ---
try:
    api_key = st.secrets["airtable"]["api_key"]
    base_id = st.secrets["airtable"]["base_id"]
    t_rec_id = st.secrets["airtable"]["table_recettes"]
    t_ing_id = st.secrets["airtable"]["table_ingredients"]
    t_course_id = st.secrets["airtable"]["table_listeDeCourses"]
except Exception as e:
    st.error("Erreur : Les secrets Airtable ne sont pas correctement configurés dans Streamlit.")
    st.stop()

# --- FONCTION DE CHARGEMENT (CORRIGÉE POUR LE CACHE) ---
@st.cache_data(ttl=60)
def fetch_airtable_data(_api_key, _base_id, table_id):
    # On crée l'objet Table ici pour éviter l'erreur UnhashableParamError
    table = Table(_api_key, _base_id, table_id)
    records = table.all()
    # On aplatit les données et on garde l'ID unique de chaque ligne
    return pd.DataFrame([ {**r['fields'], 'airtable_id': r['id']} for r in records ])

# Chargement des DataFrames
df_recettes = fetch_airtable_data(api_key, base_id, t_rec_id)
df_ingredients = fetch_airtable_data(api_key, base_id, t_ing_id)
df_courses = fetch_airtable_data(api_key, base_id, t_course_id)

# --- INTERFACE ---
st.title("🍸 Cocktail Manager")
st.write("Calcul automatique des besoins et stocks")

if not df_recettes.empty:
    # 1. On identifie la colonne du nom
    col_nom_cocktail = 'Nom' if 'Nom' in df_recettes.columns else df_recettes.columns[0]
    
    # 2. NETTOYAGE : On enlève les valeurs vides (NaN) pour éviter l'erreur de tri
    liste_noms = df_recettes[col_nom_cocktail].dropna().unique()
    
    # 3. TRI : On trie maintenant que c'est propre
    cocktails_tries = sorted(liste_noms)
    
    choix_cocktail = st.selectbox("Quel cocktail préparez-vous ?", cocktails_tries)
    pax = st.number_input("Nombre d'invités (PAX)", min_value=1, value=50, step=1)

    if st.button("CALCULER MA LISTE"):
        st.divider()
        
        # 1. Trouver l'ID interne du cocktail sélectionné
        id_interne_cocktail = df_recettes[df_recettes[col_nom_cocktail] == choix_cocktail]['airtable_id'].values[0]
        
        # 2. Filtrer la table Ingrédients (Compositions)
        # On cherche les lignes où la colonne 'Recettes' contient notre ID
        if 'Recettes' in df_ingredients.columns:
            mask = df_ingredients['Recettes'].apply(lambda x: id_interne_cocktail in x if isinstance(x, list) else x == id_interne_cocktail)
            ingredients_filtrés = df_ingredients[mask]
            
            if not ingredients_filtrés.empty:
                st.subheader(f"Besoins pour {pax} {choix_cocktail}")
                
                for _, row in ingredients_filtrés.iterrows():
                    # On récupère les infos de l'ingrédient
                    # Note : Ajuste 'Nom' ou 'Ingrédient' selon ton Airtable
                    nom_ing = row.get('Nom', 'Sans nom')
                    qty_unitaire = row.get('Quantité', 0)
                    unite = row.get('Unité', 'cl')
                    besoin_total = qty_unitaire * pax
                    
                    # Carte d'affichage
                    st.markdown(f"""
                        <div class="card">
                            <div class="ing-title">{nom_ing}</div>
                            <div>Besoin total : <b>{besoin_total} {unite}</b></div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # 3. Lien avec la table "Liste de courses" (Formats/Marques)
                    # On compare le nom de l'ingrédient
                    if not df_courses.empty and 'Ingrédient' in df_courses.columns:
                        formats = df_courses[df_courses['Ingrédient'] == nom_ing]
                        
                        if not formats.empty:
                            cols = st.columns(len(formats))
                            for i, (_, f) in enumerate(formats.iterrows()):
                                try:
                                    contenance = float(f.get('Contenance', 1))
                                    nb_bout = math.ceil(besoin_total / contenance)
                                    with cols[i]:
                                        st.metric(label=f.get('Marque', 'Standard'), value=f"{nb_bout}")
                                        st.caption(f"Format {contenance} {f.get('Unité', 'cl')}")
                                except:
                                    continue
                        else:
                            st.caption(f"ℹ️ Aucun format de bouteille défini pour {nom_ing}")
            else:
                st.warning("Aucun ingrédient lié à ce cocktail n'a été trouvé.")
        else:
            st.error("La colonne 'Recettes' est introuvable dans la table Ingrédients.")
else:
    st.info("Ajoutez des cocktails dans votre base Airtable pour commencer.")

st.divider()
st.caption("Données synchronisées en temps réel avec Airtable")
