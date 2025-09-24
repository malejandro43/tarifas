import os
import base64
import uuid
from io import BytesIO
import pdfplumber
import pandas as pd
import re
import streamlit as st
from pypdf import PdfReader


st.set_page_config(page_title="Lector de Tablas PDF", layout="wide")

st.title("📑 Cubicaje y costo de fletes")
epes_cfs=.11
epes_terminal_change=.25
epes_docs_handling=70
epes_pikcup=.22
epes_fsc_sec=.75
epes_handling=40
epes_doc_fee=35
epes_val=15
epes_tarifa = None

bdp_hk=.36
bdp_handling=65
bdp_ams=32
bdp_fsc=1.68
bdp_ssc=.25
bdp_descon=55
bdp_tarifa=None

tcu_ams=.9
tcu_tc=.22
tcu_handling=60
tcu_pickup=.18
tcu_tarifa_hk_nr_larga_mex=None
tcu_tarifa_hk_stn_larga_mex=None
tcu_tarifa_corta=None
tcu_tarifa_hk_anc_mex=None
tcu_fsc=.55
tcu_ssc=.23


# Subir archivo
pdf_file = st.file_uploader("Sube un archivo PDF con tablas", type=["pdf"], accept_multiple_files=True)

if pdf_file:
    st.success("✅ Archivo cargado correctamente")
    
    # # Abrir el PDF con pdfplumber
    # with pdfplumber.open(pdf_file) as pdf:
    #     tablas_extraidas = []
    #     for i, page in enumerate(pdf.pages, start=1):
    #         tablas = page.extract_tables()
    #         if tablas:
    #             for tabla in tablas:
    #                 num_cols = len(tabla[0])  # primera fila = encabezados
    #                 columnas = [f"col_{i}" for i in range(num_cols)]
    #                 df = pd.DataFrame(tabla, columns=columnas)
    #                 tablas_extraidas.append((i, df))
    
    # if tablas_extraidas:
    #     st.subheader("📊 Tablas encontradas en el PDF")
    #     for pagina, df in tablas_extraidas:
    #         st.write(f"**Página {pagina}**")
    #         st.dataframe(df)
    # else:
    #     st.warning("⚠️ No se detectaron tablas en el PDF")
    
xlsx_path = "C:/Users/m_ale/Downloads/proyectos/tarifas/lista de paises.xlsx"
sheets = pd.read_excel(xlsx_path, sheet_name=None)
sheets = {}
if os.path.exists(xlsx_path):
    try:
        sheets = pd.read_excel(xlsx_path, sheet_name=None)
    except Exception as e:
        st.warning(f"No se pudo leer el Excel: {e}")
else:
    st.info("ℹ️ No se encontró el archivo de países en la ruta configurada.")

def lista_paises_desde_sheets(sheets_dict: dict) -> list:
    """
    Devuelve una lista ordenada de países/territorios a partir de la hoja
    'paises y territorios' dentro del diccionario `sheets_dict`.
    Prioriza la columna exacta 'Paises y Territorios'.
    """
    df = None
    if isinstance(sheets_dict, dict) and "paises y territorios" in sheets_dict:
        df = sheets_dict["paises y territorios"].copy()
    else:
        # Fallback directo por si sheets no trae la hoja pero el archivo existe
        for path_try in [xlsx_path, "/mnt/data/lista de paises.xlsx"]:
            if os.path.exists(path_try):
                try:
                    df = pd.read_excel(path_try, sheet_name="paises y territorios")
                    break
                except Exception:
                    pass

    if df is None or df.empty:
        return []

    # 1) Intentar columna exacta
    if "Paises y Territorios" in df.columns:
        col_key = "Paises y Territorios"
    else:
        # 2) Fallback: detección por nombres comunes
        cols_lower = {c.lower(): c for c in df.columns}
        col_key = None
        for candidate in ["país", "pais", "paises y territorios", "países y territorios", "country", "nombre", "name"]:
            if candidate in cols_lower:
                col_key = cols_lower[candidate]
                break
        # 3) Último recurso: primera columna tipo texto
        if col_key is None:
            obj_cols = [c for c in df.columns if df[c].dtype == "object"]
            col_key = obj_cols[0] if obj_cols else df.columns[0]

    valores = (
        df[col_key]
        .dropna()
        .astype(str)
        .str.strip()
    )
    valores = valores[valores != ""].unique().tolist()
    valores.sort()
    return valores

def lista_paises_desde_sheets_dhl(sheets_dict: dict) -> list:
    """
    Devuelve una lista ordenada de países/territorios a partir de la hoja
    'paises y territorios' dentro del diccionario `sheets_dict`.
    Prioriza la columna exacta 'Paises y Territorios'.
    """
    df = None
    if isinstance(sheets_dict, dict) and "DHL lista paises" in sheets_dict:
        df = sheets_dict["DHL lista paises"].copy()
    else:
        # Fallback directo por si sheets no trae la hoja pero el archivo existe
        for path_try in [xlsx_path, "/mnt/data/lista de paises.xlsx"]:
            if os.path.exists(path_try):
                try:
                    df = pd.read_excel(path_try, sheet_name="DHL lista paises")
                    break
                except Exception:
                    pass

    if df is None or df.empty:
        return []

    # 1) Intentar columna exacta
    if "País" in df.columns:
        col_key = "País"
    else:
        # 2) Fallback: detección por nombres comunes
        cols_lower = {c.lower(): c for c in df.columns}
        col_key = None
        for candidate in ["país", "pais", "paises", "países", "country", "nombre", "name"]:
            if candidate in cols_lower:
                col_key = cols_lower[candidate]
                break
        # 3) Último recurso: primera columna tipo texto
        if col_key is None:
            obj_cols = [c for c in df.columns if df[c].dtype == "object"]
            col_key = obj_cols[0] if obj_cols else df.columns[0]

    valores = (
        df[col_key]
        .dropna()
        .astype(str)
        .str.strip()
    )
    valores = valores[valores != ""].unique().tolist()
    valores.sort()
    return valores
def cubicaje_ui(prefix: str = ""):
    st.markdown("#### 📦 Datos del envío (cm / kg)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        largo = st.number_input("Largo (cm)", min_value=0.0, step=0.1, key=f"{prefix}_largo")
    with c2:
        ancho = st.number_input("Ancho (cm)", min_value=0.0, step=0.1, key=f"{prefix}_ancho")
    with c3:
        altura = st.number_input("Altura (cm)", min_value=0.0, step=0.1, key=f"{prefix}_altura")
    with c4:
        peso = st.number_input("Peso real (kg)", min_value=0.0, step=0.1, key=f"{prefix}_peso")

    volumen = 0.0
    if largo and ancho and altura:
        volumen = (largo * ancho * altura) / 5000.0  # kg volumétricos

    # Mostrar resultados
    st.markdown("#### 📐 Cálculo")
    col_a, col_b, col_c = st.columns([1,1,1])

    # Formateo
    v_str = f"{volumen:,.2f} kg"
    p_str = f"{peso:,.2f} kg"

    # Determinar mayor para resaltar
    es_volumen_mayor = volumen >= (peso or 0.0)

    with col_a:
        if es_volumen_mayor:
            st.markdown(f":red[**Volumen (kg vol.): {v_str}**]")
        else:
            st.markdown(f"Volumen (kg vol.): {v_str}")

    with col_b:
        if not es_volumen_mayor:
            st.markdown(f":red[**Peso real: {p_str}**]")
        else:
            st.markdown(f"Peso real: {p_str}")

    # Peso facturable (el mayor)
    peso_facturable = max(volumen, (peso or 0.0))
    with col_c:
        st.markdown(f"**Peso facturable:** :red[**{peso_facturable:,.2f} kg**]")

    st.caption("Fórmula: volumen (kg) = (largo × ancho × altura) / 5000")
    
    
def buscar_tarifas_fedex(sheets_dict: dict, pais_origen: str):
    """
    Busca el país en la hoja 'paises y territorios' (columna 'Paises y Territorios')
    y devuelve un DataFrame con las columnas:
    - International First
    - International Connect Plus
    - All Other Products

    Guarda además el resultado en st.session_state['fedex_tarifas'].
    """
    hoja = "paises y territorios"
    col_pais = "Paises y Territorios"
    cols_tarifas = ["International First", "International Connect Plus", "All Other Products"]

    # Validaciones básicas
    if not isinstance(sheets_dict, dict) or hoja not in sheets_dict:
        st.error("No se encontró la hoja 'paises y territorios' en el Excel.")
        return None

    df = sheets_dict[hoja]
    if df is None or df.empty:
        st.error("La hoja 'paises y territorios' está vacía.")
        return None

    # Verificar columnas requeridas
    faltantes = [c for c in [col_pais] + cols_tarifas if c not in df.columns]
    if faltantes:
        st.error(f"Faltan columnas en el Excel: {', '.join(faltantes)}")
        return None

    # Normalización para búsqueda robusta
    df = df.copy()
    df[col_pais] = df[col_pais].astype(str).str.strip()
    pais_norm = str(pais_origen).strip()

    # Búsqueda exacta (case-insensitive)
    mask = df[col_pais].str.casefold() == pais_norm.casefold()
    match = df[mask]

    if match.empty:
        st.warning(f"No se encontró el país '{pais_origen}' en 'paises y territorios'.")
        return None

    # Tomamos la primera coincidencia si hubiera varias
    row = match.iloc[0]
    tarifas_df = pd.DataFrame({
        "Producto": cols_tarifas,
        "Valor": [row[c] for c in cols_tarifas]
    })

    st.session_state["fedex_tarifas"] = tarifas_df
    return tarifas_df

def get_peso_facturable(prefix: str) -> float:
    """Lee largo/ancho/altura/peso desde session_state y calcula el peso facturable."""
    largo = float(st.session_state.get(f"{prefix}_largo", 0) or 0)
    ancho = float(st.session_state.get(f"{prefix}_ancho", 0) or 0)
    altura = float(st.session_state.get(f"{prefix}_altura", 0) or 0)
    peso = float(st.session_state.get(f"{prefix}_peso", 0) or 0)

    vol = 0.0
    if largo > 0 and ancho > 0 and altura > 0:
        vol = (largo * ancho * altura) / 5000.0
    return max(vol, peso), vol, peso


def _find_col(df: pd.DataFrame, target: str):
    """Busca una columna por nombre exacto o insensible a mayúsculas/acentos básicos."""
    if target in df.columns:
        return target
    lowmap = {c.lower(): c for c in df.columns}
    t = target.lower()
    # normalizaciones mínimas
    t = t.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    cand = None
    for k, v in lowmap.items():
        k_norm = k.replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
        if k_norm == t:
            cand = v
            break
    return cand


def _ceil_to_next_bracket(weights_series: pd.Series, value: float):
    """Devuelve el escalón más pequeño >= value; si no hay, devuelve el máximo disponible."""
    s = pd.to_numeric(weights_series, errors="coerce").dropna().sort_values().unique()
    for w in s:
        if value <= w + 1e-9:
            return float(w)
    return float(s[-1]) if len(s) else None


def cotizar_fedex_imp(sheets_dict: dict, pais_origen: str, peso_facturable: float) -> pd.DataFrame | None:
    """
    Usa:
      - Hoja 'paises y territorios' (col 'Paises y Territorios' + columnas de zona)
      - Hojas de tarifas:
        * 'FedEx International First Imp'        (para 'International First')
        * 'FedEx International connect imp'      (para 'International Connect Plus')
        * 'FedEx International Pri ExpImp'       (parte de 'All Other Products')
        * 'FedEx International Prio Imp'         (parte de 'All Other Products')
        * 'FedEx International Economy Imp'      (parte de 'All Other Products')
    Lógica:
      - Toma la letra de zona del país para cada producto.
      - En la hoja correspondiente, busca Peso (kg) y la columna 'Zona {letra}'.
      - Redondea el peso hacia el siguiente bracket disponible.
      - Precio = peso_redondeado * valor_zona.
    """
    # Validaciones mínimas
    if "paises y territorios" not in sheets_dict:
        st.error("No se encontró la hoja 'paises y territorios'.")
        return None

    df_paises = sheets_dict["paises y territorios"].copy()
    col_pais = _find_col(df_paises, "Paises y Territorios")
    if not col_pais:
        st.error("No se encontró la columna 'Paises y Territorios' en 'paises y territorios'.")
        return None

    # Filtrar país
    mask = df_paises[col_pais].astype(str).str.strip().str.casefold() == str(pais_origen).strip().casefold()
    match = df_paises[mask]
    if match.empty:
        st.warning(f"No se encontró el país '{pais_origen}' en 'paises y territorios'.")
        return None
    row = match.iloc[0]

    # Columnas de zona que vienen del botón previo (coinciden con buscar_tarifas_fedex)
    # International First, International Connect Plus, All Other Products
    col_if  = _find_col(df_paises, "International First")
    col_icp = _find_col(df_paises, "International Connect Plus")
    col_aop = _find_col(df_paises, "All Other Products")
    if not all([col_if, col_icp, col_aop]):
        st.error("Faltan columnas de zonas (IF/ICP/AOP) en 'paises y territorios'.")
        return None

    zona_if  = str(row[col_if]).strip()
    zona_icp = str(row[col_icp]).strip()
    zona_aop = str(row[col_aop]).strip()

    # Mapeo producto -> hojas
    producto_to_sheets = {
        "International First": ["FedEx International First Imp"],
        "International Connect Plus": ["FedEx International connect imp"],
        "All Other Products": [
            "FedEx International Pri ExpImp",
            "FedEx International Prio Imp",
            "FedEx International Economy Imp",
        ],
    }
    # Mapeo producto -> zona letra
    producto_to_zona = {
        "International First": zona_if,
        "International Connect Plus": zona_icp,
        "All Other Products": zona_aop,
    }

    resultados = []
    for producto, hojas in producto_to_sheets.items():
        zona_letra = producto_to_zona[producto]
        if not zona_letra or zona_letra.lower() in ("nan", "none", ""):
            resultados.append({
                "Producto": producto,
                "Hoja": ", ".join(hojas),
                "Zona": "(sin zona)",
                "Peso (kg) redondeado": None,
                "Tarifa por kg": None,
                "Precio": None,
                "Nota": "Sin zona para el país"
            })
            continue

        for hoja in hojas:
            if hoja not in sheets_dict:
                resultados.append({
                    "Producto": producto,
                    "Hoja": hoja,
                    "Zona": zona_letra,
                    "Peso (kg) redondeado": None,
                    "Tarifa por kg": None,
                    "Precio": None,
                    "Nota": "Hoja no encontrada"
                })
                continue

            df_tarifa = sheets_dict[hoja].copy()
            col_peso = _find_col(df_tarifa, "Peso (kg)")
            col_zona = _find_col(df_tarifa, f"Zona {zona_letra}")
            if not col_peso or not col_zona:
                resultados.append({
                    "Producto": producto,
                    "Hoja": hoja,
                    "Zona": zona_letra,
                    "Peso (kg) redondeado": None,
                    "Tarifa por kg": None,
                    "Precio": None,
                    "Nota": "No se encontró 'Peso (kg)' o la columna de zona"
                })
                continue

            # Redondeo al siguiente bracket
            peso_red = _ceil_to_next_bracket(df_tarifa[col_peso], peso_facturable)
            if peso_red is None:
                resultados.append({
                    "Producto": producto,
                    "Hoja": hoja,
                    "Zona": zona_letra,
                    "Peso (kg) redondeado": None,
                    "Tarifa por kg": None,
                    "Precio": None,
                    "Nota": "Tabla de pesos vacía"
                })
                continue

            # Obtener la tarifa por kg del escalón encontrado
            fila = df_tarifa[pd.to_numeric(df_tarifa[col_peso], errors="coerce") == peso_red]
            if fila.empty:
                # fallback: si hubo issues de flotantes, aproximar
                idx = (pd.to_numeric(df_tarifa[col_peso], errors="coerce") - peso_red).abs().idxmin()
                fila = df_tarifa.loc[[idx]]

            tarifa_kg = pd.to_numeric(fila.iloc[0][col_zona], errors="coerce")
            if pd.isna(tarifa_kg):
                resultados.append({
                    "Producto": producto,
                    "Hoja": hoja,
                    "Zona": zona_letra,
                    "Peso (kg) redondeado": peso_red,
                    "Tarifa por kg": None,
                    "Precio": None,
                    "Nota": "Tarifa por kg no numérica"
                })
                continue

            precio = round(peso_red * float(tarifa_kg), 2)
            resultados.append({
                "Producto": producto,
                "Hoja": hoja,
                "Zona": zona_letra,
                "Peso (kg) redondeado": peso_red,
                "Tarifa por kg": float(tarifa_kg),
                "Precio": precio,
                "Nota": ""
            })

    res_df = pd.DataFrame(resultados)
    return res_df
def buscar_zona_dhl(sheets_dict: dict, pais_origen: str):
    """
    Busca el país en la hoja 'DHL lista paises' (col 'País') y devuelve un DataFrame con:
      - País
      - Zona

    También guarda el resultado en st.session_state['dhl_imp_zona_df'].
    """
    hoja = "DHL lista paises"
    if hoja not in sheets_dict:
        st.error("No se encontró la hoja 'DHL lista paises' en el Excel.")
        return None

    df = sheets_dict[hoja]
    if df is None or df.empty:
        st.error("La hoja 'DHL lista paises' está vacía.")
        return None

    col_pais = _find_col(df, "País") or _find_col(df, "Pais")
    col_zona = _find_col(df, "Zona")
    if not col_pais or not col_zona:
        st.error("No se encontraron columnas 'País'/'Zona' en 'DHL lista paises'.")
        return None

    df = df.copy()
    df[col_pais] = df[col_pais].astype(str).str.strip()
    pais_norm = str(pais_origen).strip()

    mask = df[col_pais].str.casefold() == pais_norm.casefold()
    match = df[mask]

    if match.empty:
        st.warning(f"No se encontró el país '{pais_origen}' en 'DHL lista paises'.")
        return None

    # Tomamos la primera coincidencia
    row = match.iloc[0]
    zona = str(row[col_zona]).strip()

    zona_df = pd.DataFrame({
        "País": [pais_origen],
        "Zona": [zona]
    })

    st.session_state["dhl_imp_zona_df"] = zona_df
    return zona_df
def cotizar_dhl_imp(sheets_dict: dict, pais_origen: str, peso_facturable: float) -> pd.DataFrame | None:
    """
    Usa:
      - 'DHL lista paises' (col 'País' + 'Zona') para obtener la zona 1..6 del país.
      - 'EXPRESS WORLDWIDE IMPORT non Do' para tomar:
           'Kilos' y la columna por zona:
              1 -> 'Norteamérica (1)'
              2 -> 'LATAM (2)'
              3 -> 'Caribe (3)'
              4 -> 'Unión Europea (4)'
              5 -> 'Principales economías Asia Pacífico (5)'
              6 -> 'Resto del mundo (6)'
    Lógica:
      - Redondea el peso al siguiente bracket disponible en 'Kilos' (ceil).
      - Precio = peso_redondeado * valor_columna_zona.
    """
    hoja_paises = "DHL lista paises"
    hoja_tarifas = "EXPRESS WORLDWIDE IMPORT non Do"

    if hoja_paises not in sheets_dict:
        st.error("No se encontró la hoja 'DHL lista paises'.")
        return None
    if hoja_tarifas not in sheets_dict:
        st.error("No se encontró la hoja 'EXPRESS WORLDWIDE IMPORT non Do'.")
        return None

    # 1) Obtener zona del país
    df_zonas = sheets_dict[hoja_paises].copy()
    col_pais = _find_col(df_zonas, "País") or _find_col(df_zonas, "Pais")
    col_zona = _find_col(df_zonas, "Zona")
    if not col_pais or not col_zona:
        st.error("No se encontraron columnas 'País'/'Zona' en 'DHL lista paises'.")
        return None

    df_zonas[col_pais] = df_zonas[col_pais].astype(str).str.strip()
    mask = df_zonas[col_pais].str.casefold() == str(pais_origen).strip().casefold()
    match = df_zonas[mask]
    if match.empty:
        st.warning(f"No se encontró el país '{pais_origen}' en 'DHL lista paises'.")
        return None

    zona_val = str(match.iloc[0][col_zona]).strip()
    if zona_val == "" or zona_val.lower() in ("nan", "none"):
        st.warning(f"'{pais_origen}' no tiene zona válida en 'DHL lista paises'.")
        return None

    # 2) Elegir columna de tarifas por zona
    zona_map = {
        "1": "Norteamérica (1)",
        "2": "LATAM (2)",
        "3": "Caribe (3)",
        "4": "Unión Europea (4)",
        "5": "Principales economías Asia Pacífico (5)",
        "6": "Resto del mundo (6)",
    }
    zona_key = None
    # admite que zona pueda venir como int/float
    z_norm = re.sub(r"[^\d]", "", zona_val)
    if z_norm in zona_map:
        zona_key = zona_map[z_norm]
    else:
        # fallback por si la zona es algo como "Zona 4" o "4.0"
        for k in zona_map:
            if k in zona_val:
                zona_key = zona_map[k]
                break

    if not zona_key:
        st.error(f"No se pudo mapear la zona '{zona_val}' a una columna de tarifas DHL.")
        return None

    # 3) Buscar en la hoja de tarifas
    df_tarifas = sheets_dict[hoja_tarifas].copy()
    col_kilos = _find_col(df_tarifas, "Kilos")
    col_tarifa = _find_col(df_tarifas, zona_key)
    if not col_kilos or not col_tarifa:
        st.error(f"No se encontró 'Kilos' o la columna '{zona_key}' en '{hoja_tarifas}'.")
        return None

    # 4) Redondeo hacia el siguiente escalón de 'Kilos'
    peso_red = _ceil_to_next_bracket(df_tarifas[col_kilos], peso_facturable)
    if peso_red is None:
        st.warning("La tabla de 'Kilos' está vacía en DHL.")
        return None

    fila = df_tarifas[pd.to_numeric(df_tarifas[col_kilos], errors="coerce") == peso_red]
    if fila.empty:
        idx = (pd.to_numeric(df_tarifas[col_kilos], errors="coerce") - peso_red).abs().idxmin()
        fila = df_tarifas.loc[[idx]]

    tarifa_kg = pd.to_numeric(fila.iloc[0][col_tarifa], errors="coerce")
    if pd.isna(tarifa_kg):
        st.warning("La tarifa por kg no es numérica en la fila seleccionada.")
        return None

    #precio = round(float(peso_red) * float(tarifa_kg), 2)

    return pd.DataFrame([{
        "País": pais_origen,
        "Zona": zona_val,
        "Columna zona": zona_key,
        "Peso (kg) ": round(peso_facturable, 2),
        "Tarifa": float(tarifa_kg),
     #   "Precio": float(precio),
    }])
    
def cubicaje_forwarder_ui(prefix: str):
    st.markdown("#### 📦 Cálculo de cubicaje (mts / kg)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        largo = st.number_input("Largo (mts)", min_value=0.0, step=0.1, key=f"{prefix}_largo")
    with c2:
        ancho = st.number_input("Ancho (mts)", min_value=0.0, step=0.1, key=f"{prefix}_ancho")
    with c3:
        altura = st.number_input("Altura (mts)", min_value=0.0, step=0.1, key=f"{prefix}_altura")
    with c4:
        peso = st.number_input("Peso real (kg por caja)", min_value=0.0, step=0.1, key=f"{prefix}_peso")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        cajas = st.number_input("Cantidad de cajas", min_value=1, step=1, value=1, key=f"{prefix}_cajas")
    with col_c2:
        peso_total_cajas = st.number_input(
            "Peso total de las cajas (kg, opcional)",
            min_value=0.0, step=0.1, value=0.0,
            key=f"{prefix}_peso_total"
        )

    # Volumétrico y facturable por caja
    vol = 0.0
    if largo and ancho and altura:
        vol = (largo * ancho * altura) * 166.66  # kg volumétricos

    facturable = max(vol, peso)

    # Total facturable (considerando cajas)
    total_facturable = facturable * cajas

    # Si se ingresó peso total de las cajas, se toma como referencia
    if peso_total_cajas > 0:
        total_facturable = max(vol * cajas, peso_total_cajas)

    st.markdown("#### 📐 Resultados")
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        if vol >= peso:
            st.markdown(f":red[**Volumen: {vol:,.2f} kg**]")
        else:
            st.markdown(f"Volumen: {vol:,.2f} kg")
    with r2:
        if peso > vol:
            st.markdown(f":red[**Peso real (x caja): {peso:,.2f} kg**]")
        else:
            st.markdown(f"Peso real (x caja): {peso:,.2f} kg")
    with r3:
        st.markdown(f"**Peso facturable (x caja):** :red[**{facturable:,.2f} kg**]")
    with r4:
        st.markdown(f"**Total facturable:** :red[**{total_facturable:,.2f} kg**]")

    if peso_total_cajas > 0:
        st.caption("⚠️ Se usó el **Peso total de las cajas** como referencia en lugar de Peso real × cajas.")

    st.caption("Fórmula: (Largo × Ancho × Altura) * 166.66")
    return {
        "volumen": vol,
        "peso_real": peso,
        "facturable": facturable,
        "cajas": int(cajas),
        "peso_total_cajas": peso_total_cajas,
        "total_facturable": total_facturable
    }
def calcular_epes_total_flete(total_facturable: float) -> dict:
    """
    Calcula total_flete para EPES Logistic:
      - cargos_origen = epes_cfs*TF + epes_terminal_change*TF + epes_docs_handling + epes_pikcup*TF
      - flete por bandas:
          TF < 45        -> usa tarifa de 10.3 (asumimos banda 45 kg)
          45 ≤ TF < 100  -> 10.3
          100 ≤ TF < 500 -> 10.25
          500 ≤ TF < 1000-> 9.9
          TF ≥ 1000      -> 9.7
      - total_flete = cargos_origen + flete + epes_fsc_sec*TF
    """
    tf = float(total_facturable or 0.0)

    # ---- cargos de origen ----
    cargos_origen = (
        epes_cfs * tf
        + epes_terminal_change * epes_cfs * tf
        + epes_docs_handling
        + epes_pikcup * tf
    )

    # ---- tarifa por kg según rangos ----
    if tf < 45:
        tarifa_kg = 10.3   # asumimos banda 45 kg
    elif 45 <= tf < 100:
        tarifa_kg = 10.3
    elif 100 <= tf < 500:
        tarifa_kg = 10.25
    elif 500 <= tf < 1000:
        tarifa_kg = 9.9
    else:  # tf >= 1000
        tarifa_kg = 9.7

    flete = tf * tarifa_kg

    # ---- total ----
    total_flete = cargos_origen + flete + epes_fsc_sec * tf

    return {
        "TF": round(tf, 2),
        "tarifa_kg": tarifa_kg,
        "cargos_origen": round(cargos_origen, 2),
        "flete": round(flete, 2),
        "fsc_sec_total": round(epes_fsc_sec * tf, 2),
        "total_flete": round(total_flete, 2),
    }

def calcular_bdp_total_flete(total_facturable: float) -> dict:
    """
    Calcula flete total para BDP:
      cargos_origen = bdp_hk*TF + bdp_handling + bdp_ams
      bdp_tarifa (USD/kg) por rangos:
        TF < 45           -> usa banda 45–100 => 9.25  (asunción)
        45 ≤ TF < 100     -> 9.25
        100 ≤ TF < 500    -> 9.20
        500 ≤ TF < 1000   -> 9.15
        TF ≥ 1000         -> 9.12   (interpreto tu "más de 100" como >1000)
      flete = TF*bdp_tarifa + TF*bdp_fsc + TF*bdp_ssc
      flete_total = cargos_origen + flete + bdp_descon
    """
    tf = float(total_facturable or 0.0)

    # cargos de origen
    cargos_origen = (bdp_hk * tf) + bdp_handling + bdp_ams

    # tarifa por kg según bandas
    if tf < 45:
        tarifa_kg = 9.25  # asunción: se cobra como banda 45–100
    elif 45 <= tf < 100:
        tarifa_kg = 9.25
    elif 100 <= tf < 500:
        tarifa_kg = 9.20
    elif 500 <= tf < 1000:
        tarifa_kg = 9.15
    else:  # tf >= 1000
        tarifa_kg = 9.12

    # flete
    flete = tf * tarifa_kg + tf * bdp_fsc + tf * bdp_ssc

    # total
    flete_total = cargos_origen + flete + bdp_descon

    return {
        "TF": round(tf, 2),
        "tarifa_kg": tarifa_kg,
        "cargos_origen": round(cargos_origen, 2),
        "flete": round(flete, 2),
        "flete_total": round(flete_total, 2),
    }
def _tarifa_transcargo_por_ruta(tf: float, ruta: str) -> float:
    """
    Devuelve la tarifa USD/kg según la ruta y el TF.
    Rutas soportadas:
      - "HKG–NRT–LA–MEX (5–6 días)"
      - "HKG–STN–LHR–MEX (5–6 días)"
      - "HKG–LAX–MEX (1–2 días)"
      - "HKG–ANC–SDF–MEX (5–6 días)"
    """
    x = float(tf or 0.0)
    # Normaliza TF<45 a la banda 45–100
    if x < 45:
        x_norm = 45.0
    else:
        x_norm = x

    if ruta == "HKG–NRT–LA–MEX (5–6 días)":
        # tcu_tarifa_hk_anc_mex (según tu instrucción)
        if 45 <= x_norm < 100:
            return 9.73
        elif 100 <= x_norm < 300:
            return 9.26
        elif 300 <= x_norm < 500:
            return 9.13
        elif 500 <= x_norm < 1000:
            return 8.88
        else:  # >= 1000
            return 8.60

    elif ruta == "HKG–STN–LHR–MEX (5–6 días)":
        # tcu_tarifa_hk_stn_larga_mex
        if 45 <= x_norm < 100:
            return 8.96
        elif 100 <= x_norm < 300:
            return 8.90
        elif 300 <= x_norm < 500:
            return 8.34
        elif 500 <= x_norm < 1000:
            return 8.06
        else:  # >= 1000
            return 8.87

    elif ruta == "HKG–LAX–MEX (1–2 días)":
        # tcu_tarifa_corta
        if 45 <= x_norm < 100:
            return 10.60
        elif 100 <= x_norm < 300:
            return 10.50
        elif 300 <= x_norm < 500:
            return 10.34
        elif 500 <= x_norm < 1000:
            return 10.20
        else:  # >= 1000
            return 10.02

    elif ruta == "HKG–ANC–SDF–MEX (5–6 días)":
        # tcu_tarifa_hk_anc_mex (segunda tabla que diste para esta ruta)
        if 45 <= x_norm < 100:
            return 9.65
        elif 100 <= x_norm < 300:
            return 9.39
        elif 300 <= x_norm < 500:
            return 9.15
        elif 500 <= x_norm < 1000:
            return 9.05
        else:  # >= 1000
            return 8.98

    # Ruta desconocida
    return 0.0


def calcular_transcargo_totales(total_facturable: float) -> pd.DataFrame:
    """
    Calcula los 4 fletes totales para Transcargo Universal con tus reglas.
    Retorna un DataFrame con columnas:
      Ruta, TF, Tarifa (USD/kg), Cargos origen, Flete base, FSC, SSC, FLETE TOTAL
    """
    tf = float(total_facturable or 0.0)

    # Cargos de origen
    cargos_origen = (tcu_ams * tf) + (tcu_tc * tf) + tcu_handling + (tcu_pickup * tf)

    rutas = [
        "HKG–NRT–LA–MEX (5–6 días)",
        "HKG–STN–LHR–MEX (5–6 días)",
        "HKG–LAX–MEX (1–2 días)",
        "HKG–ANC–SDF–MEX (5–6 días)",
    ]

    rows = []
    for ruta in rutas:
        tarifa = _tarifa_transcargo_por_ruta(tf, ruta)
        flete_base = tf * tarifa
        fsc_val = tf * tcu_fsc
        ssc_val = tf * tcu_ssc
        total = cargos_origen + flete_base + fsc_val + ssc_val

        rows.append({
            "Ruta": ruta,
            "TF (kg)": round(tf, 2),
            "Tarifa (USD/kg)": tarifa,
            "Cargos origen (USD)": round(cargos_origen, 2),
            "Flete base (USD)": round(flete_base, 2),
            "FSC (USD)": round(fsc_val, 2),
            "SSC (USD)": round(ssc_val, 2),
            "FLETE TOTAL (USD)": round(total, 2),
        })

    return pd.DataFrame(rows)
# --- Tabs principales ---
tab_paq, tab_fwd = st.tabs(["📮 Paqueterías", "🚢 Forwarders"])

with tab_paq:
    st.subheader("Paqueterías")
    # Opción para el usuario: Importación / Exportación
    modo_paq = st.radio(
        "Selecciona el tipo de operación",
        options=["Importación", "Exportación"],
        horizontal=True
    )

    # Contenedor dinámico según selección
    if modo_paq == "Importación":
        with st.container(border=True):
            st.markdown("### 📥 Importación FedEx")
            paises_opciones = lista_paises_desde_sheets(sheets)
            if not paises_opciones:
                st.warning("No se encontraron países en la hoja 'paises y territorios'. Revisa el Excel.")
                paises_opciones = ["(Sin datos)"]
            col1, col2 = st.columns(2)
            with col1:
                origen = st.selectbox("Origen (país / territorio)",paises_opciones,key="imp_origen")
            # 🔜 Aquí agregaremos tus entradas específicas (país, courier, peso, dimensiones, reglas, etc.)
            # Ejemplo de placeholder mínimo:
            with col2:
                st.text_input("Destino", value="México", key="imp_destino", disabled=True)
            cubicaje_ui(prefix="fedex_imp")
            col_c1, col_c2 = st.columns(2)

            with col_c1:
                combustible_pct = st.number_input(
                    "Combustible (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.1,
                    value=0.0,
                    key="fedex_imp_combustible"
                )

            with col_c2:
                total_cajas = st.number_input(
                    "Total de cajas",
                    min_value=1,
                    step=1,
                    value=1,
                    key="fedex_imp_cajas"
                )

            st.caption("Resultados calculados: Precio + Combustible, y Total con cajas.")
            if st.button("🔎 Buscar tarifas FedEx", key="btn_buscar_fedex"):
                if "imp_origen" in st.session_state and st.session_state["imp_origen"] and st.session_state["imp_origen"] != "(Sin datos)":
                    tarifas_df = buscar_tarifas_fedex(sheets, st.session_state["imp_origen"])
                    if tarifas_df is not None:
                        st.success("Tarifas de FedEx encontradas y guardadas en memoria.")
                        st.dataframe(tarifas_df, use_container_width=True)
                else:
                    st.warning("Selecciona un país de origen válido antes de buscar.")
            if st.button("💰 Calcular tarifa FedEx", key="btn_cotizar_fedex"):
                # 1) Peso facturable a partir de los inputs de cubicaje (usa el mismo prefix que pusiste en cubicaje_ui)
                peso_fact, vol, p_real = get_peso_facturable(prefix="fedex_imp")

                if peso_fact <= 0:
                    st.warning("Captura largo, ancho, altura y peso para calcular el peso facturable.")
                elif "imp_origen" not in st.session_state or not st.session_state["imp_origen"] or st.session_state["imp_origen"] == "(Sin datos)":
                    st.warning("Selecciona un país de origen válido.")
                else:
                    pais = st.session_state["imp_origen"]
                    cot_df = cotizar_fedex_imp(sheets, pais, peso_fact)
                    if cot_df is not None and not cot_df.empty:
                        st.success(f"Cotización basada en peso facturable = {peso_fact:,.2f} kg (vol: {vol:,.2f} / real: {p_real:,.2f})")
                        pct = (st.session_state.get("fedex_imp_combustible", 0.0) or 0.0) / 100.0
                        cajas = int(st.session_state.get("fedex_imp_cajas", 1) or 1)
                        if "Precio" in cot_df.columns:
                            cot_df = cot_df.copy()
                            cot_df["Resultado combustible"] = (pd.to_numeric(cot_df["Precio"], errors="coerce").fillna(0.0) * pct).round(2)
                            cot_df["Total con combustible x caja"] = (pd.to_numeric(cot_df["Precio"], errors="coerce").fillna(0.0) + cot_df["Resultado combustible"]).round(2)
                            cot_df["TOTAL"] = (cot_df["Total con combustible x caja"] * cajas).round(2)
                        else:
                            st.warning("No se encontró la columna 'Precio' para aplicar el combustible.")
                        st.success(f"Cotización basada en peso facturable = {peso_fact:,.2f} kg (vol: {vol:,.2f} / real: {p_real:,.2f})")
                        st.dataframe(cot_df, use_container_width=True)
                    else:
                        st.warning("No fue posible calcular la tarifa. Revisa notas y estructura del Excel.")

            st.caption("El resultado se calcula como: Precio × (Combustible% / 100)")
            st.divider()
            
            st.markdown("### 📥 Importación DHL")
            paises_opciones = lista_paises_desde_sheets_dhl(sheets)
            if not paises_opciones:
                st.warning("No se encontraron países en la hoja 'paises y territorios'. Revisa el Excel.")
                paises_opciones = ["(Sin datos)"]
            col1, col2 = st.columns(2)
            with col1:
                origen = st.selectbox("Origen (país / territorio)",paises_opciones,key="imp_origen_dhl")
            # 🔜 Aquí agregaremos tus entradas específicas (país, courier, peso, dimensiones, reglas, etc.)
            # Ejemplo de placeholder mínimo:
            with col2:
                st.text_input("Destino", value="México", key="imp_destino_dhl", disabled=True)
            cubicaje_ui(prefix="dhl_imp")
            col_c1, col_c2 = st.columns(2)

            with col_c1:
                combustible_pct_dhl = st.number_input(
                    "Combustible (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.1,
                    value=0.0,
                    key="dhl_imp_combustible"
                )

            with col_c2:
                total_cajas_dhl = st.number_input(
                    "Total de cajas",
                    min_value=1,
                    step=1,
                    value=1,
                    key="dhl_imp_cajas"
                )

            st.caption("Resultados calculados: Precio + Combustible, y Total con cajas (DHL).")
            if st.button("🔎 Buscar zona DHL", key="btn_buscar_dhl"):
                if "imp_origen_dhl" in st.session_state and st.session_state["imp_origen_dhl"] and st.session_state["imp_origen_dhl"] != "(Sin datos)":
                    zona_df = buscar_zona_dhl(sheets, st.session_state["imp_origen_dhl"])
                    if zona_df is not None:
                        st.success("Zona DHL encontrada y guardada en memoria.")
                        st.dataframe(zona_df, use_container_width=True)
                else:
                    st.warning("Selecciona un país de origen válido antes de buscar.")
            if st.button("💰 Calcular tarifa DHL", key="btn_cotizar_dhl"):
                peso_fact, vol, p_real = get_peso_facturable(prefix="dhl_imp")

                if peso_fact <= 0:
                    st.warning("Captura largo, ancho, altura y peso para calcular el peso facturable.")
                elif "imp_origen_dhl" not in st.session_state or not st.session_state["imp_origen_dhl"] or st.session_state["imp_origen_dhl"] == "(Sin datos)":
                    st.warning("Selecciona un país de origen válido.")
                else:
                    pais = st.session_state["imp_origen_dhl"]
                    dhl_df = cotizar_dhl_imp(sheets, pais, peso_fact)
                    if dhl_df is not None and not dhl_df.empty:
                        # ⛽ aplicar combustible y total con cajas
                        pct = (st.session_state.get("dhl_imp_combustible", 0.0) or 0.0) / 100.0
                        cajas = int(st.session_state.get("dhl_imp_cajas", 1) or 1)

                        if "Tarifa" in dhl_df.columns:
                            dhl_df = dhl_df.copy()
                            dhl_df["Resultado combustible"] = (
                                pd.to_numeric(dhl_df["Tarifa"], errors="coerce").fillna(0.0) * pct
                            ).round(2)

                            dhl_df["Total con combustible"] = (
                                pd.to_numeric(dhl_df["Tarifa"], errors="coerce").fillna(0.0) + dhl_df["Resultado combustible"]
                            ).round(2)

                            dhl_df["Total con combustible y cajas"] = (
                                dhl_df["Total con combustible"] * cajas
                            ).round(2)
                        else:
                            st.warning("No se encontró la columna 'Precio' para aplicar el combustible.")

                        st.success(f"Cotización DHL con peso facturable = {peso_fact:,.2f} kg (vol: {vol:,.2f} / real: {p_real:,.2f})")
                        st.dataframe(dhl_df, use_container_width=True)
                    else:
                        st.warning("No fue posible calcular la tarifa DHL. Revisa la estructura del Excel y la zona del país.")
            st.divider()

    else:  # Exportación
        with st.container(border=True):
            st.markdown("### 📤 Exportación FedEx")
            st.caption("Configura aquí los datos de exportación. (Deja los campos para después; aquí irá la lógica que me indiques.)")
            # 🔜 Aquí agregaremos tus entradas específicas (país, courier, peso, dimensiones, reglas, etc.)
            # Ejemplo de placeholder mínimo:
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Origen (país / ciudad)", key="exp_origen", placeholder="Ej. México / CDMX")
            with col2:
                st.text_input("Destino (país / ciudad)", key="exp_destino", placeholder="Ej. USA / Miami")
            st.divider()

   
with tab_fwd:
    st.subheader("Forwarders")

    with st.expander("🟦 EPES Logistic", expanded=True):
        epes_vals = cubicaje_forwarder_ui(prefix="fw_epes")
        if st.button("💰 Calcular EPES Logistic", key="btn_epes_calc"):
            tf = epes_vals.get("total_facturable", 0.0)
            if tf <= 0:
                st.warning("Captura dimensiones/peso para obtener un Total facturable (> 0).")
            else:
                res = calcular_epes_total_flete(tf)
                st.markdown("### 🧾 EPES Logistic – Cotización")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"**Total facturable (kg):** {res['TF']:,.2f}")
                    st.markdown(f"**Tarifa (USD/kg):** {res['tarifa_kg']}")
                with c2:
                    st.markdown(f"**Cargos de origen (USD):** {res['cargos_origen']:,.2f}")
                    st.markdown(f"**Flete (USD):** {res['flete']:,.2f}")
                with c3:
                    st.markdown(f"**FSC/SEC total (USD):** {res['fsc_sec_total']:,.2f}")
                    st.markdown(f"**TOTAL FLETE (USD):** :red[**${res['total_flete']:,.2f}**]")
        st.divider()
        # epes_vals["total_facturable"] ya listo para tarifas

    with st.expander("🟧 BDP Internacional", expanded=False):
        bdp_vals = cubicaje_forwarder_ui(prefix="fw_bdp")
        if st.button("💰 Calcular BDP Internacional", key="btn_bdp_calc"):
            tf = bdp_vals.get("total_facturable", 0.0)
            if tf <= 0:
                st.warning("Captura dimensiones/peso para obtener un Total facturable (> 0).")
            else:
                res = calcular_bdp_total_flete(tf)
                st.markdown("### 🧾 BDP Internacional – Cotización")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Total facturable (kg):** {res['TF']:,.2f}")
                    st.markdown(f"**Tarifa (USD/kg):** {res['tarifa_kg']}")
                    st.markdown(f"**Cargos de origen (USD):** {res['cargos_origen']:,.2f}")
                with c2:
                    st.markdown(f"**Flete (USD):** {res['flete']:,.2f}")
                    st.markdown(f"**FLETE TOTAL (USD):** :red[**${res['flete_total']:,.2f}**]")
        st.divider()
        # bdp_vals["total_facturable"] ya listo para tarifas

    with st.expander("🟪 Transcargo Universal", expanded=False):
        trans_vals = cubicaje_forwarder_ui(prefix="fw_transcargo")
        if st.button("💰 Calcular Transcargo Universal", key="btn_transcargo_calc"):
            tf = trans_vals.get("total_facturable", 0.0)
            if tf <= 0:
                st.warning("Captura dimensiones/peso para obtener un Total facturable (> 0).")
            else:
                df_trans = calcular_transcargo_totales(tf)
                st.markdown("### 🧾 Transcargo Universal – Cotizaciones por ruta")
                st.dataframe(df_trans, use_container_width=True)
        st.divider()
        # trans_vals["total_facturable"] ya listo para tarifas