import streamlit as st
import pandas as pd
import math
from pyairtable import Table

# --- CONFIGURATION ---
st.set_page_config(page_title="Cocktail Manager", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #FF4B4B; color: white; font-weight: bold; }
    .card { background-color: white; padding: 15px; border-radius: 12px; border-left: 6px solid #FF4B4B; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .ing-title { font-weight: bold; color: #2c3e50; font-size: 1.1em; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION ---
try:
    api_key = st.secrets["airtable"]["api_key"]
    base_id = st.secrets["airtable"]["base_id"]
    t_rec_id = st.secrets["airtable"]["table_recettes"]
    t_ing_id = st.secrets["airtable"]["table_ingredients"]
    t_course_id = st.secrets["airtable"]["table_listeDeCourses"]
except Exception as e:
    st.error("Erreur de configuration des secrets Airtable.")
    st.stop()

@st.cache_data(ttl=60)
def fetch_airtable_data(_api_key, _base_id, table_id):
    table = Table(_api_key, _base_id, table_id)
    records = table.all()
    return pd.DataFrame([ {**r['fields'], 'airtable_id': r['id']} for r in records ])

# Chargement
df_recettes = fetch_airtable_data(api_key, base_id, t_rec_id)
df_ingredients = fetch_airtable_data(api_key, base_id, t_ing_id)
df_courses = fetch_airtable_data(api_key, base_id, t_course_id)

st.title("🍸 Cocktail Manager")

if not df_recettes.empty:
    col_nom_recette = 'Nom' 
    liste_cocktails = sorted(df_recettes[col_nom_recette].dropna().unique())
    choix_cocktail = st.selectbox("Quel cocktail préparez-vous ?", liste_cocktails)
    pax = st.number_input("Nombre d'invités (PAX)", min_value=1, value=50)

    if st.button("CALCULER MA LISTE"):
        st.divider()
        
        # ID du cocktail
        id_cocktail = df_recettes[df_recettes[col_nom_recette] == choix_cocktail]['airtable_id'].values[0]
        
        # Filtrage dans la table 'Ingrédients' (Colonne 'Recette')
        mask = df_ingredients['Recette'].apply(lambda x: id_cocktail in x if isinstance(x, list) else x == id_cocktail)
        mes_ingredients = df_ingredients[mask]
        
        if not mes_ingredients.empty:
            st.subheader(f"Besoins pour {pax} {choix_cocktail}")
            
            for _, row in mes_ingredients.iterrows():
                # --- CORRECTION ICI : Le nom exact de la colonne dans ton image 8070d9 ---
                nom_ing = row.get('Nom ingrédient', 'SANS NOM')
                qty_unitaire = row.get('Quantité', 0)
                unite = row.get('Unité', 'cl')
                total_besoin = qty_unitaire * pax
                
                st.markdown(f"""
                <div class="card">
                    <div class="ing-title">{nom_ing}</div>
                    <div>Besoin total : <b>{total_besoin} {unite}</b></div>
                </div>
                """, unsafe_allow_html=True)
                
                # --- LIEN AVEC LISTE DE COURSES ---
                # Dans ton image 7f101f, la colonne s'appelle 'Name'
                if not df_courses.empty:
                    # On cherche la correspondance entre 'Nom ingrédient' et 'Name'
                    formats = df_courses[df_courses['Name'] == nom_ing]
                    
                    if not formats.empty:
                        cols = st.columns(len(formats))
                        for i, (_, f) in enumerate(formats.iterrows()):
                            try:
                                # S'assurer d'avoir une colonne 'Contenance' (Nombre) dans Airtable
                                contenance = float(f.get('Contenance', 1))
                                nb_bout = math.ceil(total_besoin / contenance)
                                with cols[i]:
                                    st.metric(label=f.get('Marque', 'Standard'), value=f"{nb_bout}")
                                    st.caption(f"Format {contenance} {unite}")
                            except:
                                continue
                    else:
                        st.caption(f"ℹ️ Aucun format trouvé pour '{nom_ing}' dans la table Liste de courses.")
        else:
            st.warning("Aucun ingrédient trouvé pour ce cocktail.")
