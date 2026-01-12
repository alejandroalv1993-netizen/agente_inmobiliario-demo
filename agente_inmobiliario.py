import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import pandas as pd
import os
from datetime import datetime
import uuid

# --- 1. DATOS REALES DE LA INMOBILIARIA (Contexto) ---
INVENTARIO_REAL = """
LISTADO DE PROPIEDADES DISPONIBLES EN 'HABITAT FUTURO':

1. REF-001: Ático en Gran Vía (Madrid). Precio: 850.000€.
   - Palabras clave: ático, gran vía, terraza, vistas, lujo.

2. REF-002: Piso Familiar en Chamberí. Precio: 620.000€.
   - Palabras clave: chamberí, familiar, colegio, exterior.

3. REF-003: Loft Industrial en Malasaña. Precio: 450.000€.
   - Palabras clave: loft, malasaña, industrial, diáfano.

4. REF-004: Chalet Adosado en Aravaca. Precio: 1.2M€.
   - Palabras clave: chalet, aravaca, piscina, garaje.

CONDICIONES DE LA AGENCIA:
- Cobramos un 3% de comisión al comprador.
- Horario de visitas: Lunes a Viernes de 10:00 a 19:00.
"""

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Habitat Futuro", page_icon="🏢", layout="centered")

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .hero-title {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        color: #2C3E50;
        text-align: center;
        font-size: 2.5rem;
        margin-bottom: 0px;
    }
    .hero-subtitle {
        font-family: 'Helvetica Neue', sans-serif;
        color: #7F8C8D;
        text-align: center;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    .stButton>button {
        border-radius: 20px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- GESTIÓN DE SESIÓN ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# --- GESTIÓN DE API KEY ---
api_key = None
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
except:
    pass

# --- HELPER DE FECHAS ---
def obtener_fecha_en_espanol():
    """Devuelve la fecha actual en formato texto inequívoco"""
    ahora = datetime.now()
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    dia_txt = dias[ahora.weekday()]
    mes_txt = meses[ahora.month - 1]
    
    fecha_completa = f"{dia_txt}, {ahora.day} de {mes_txt} de {ahora.year}"
    return fecha_completa, ahora.year

# --- BARRA LATERAL (LIMPIA) ---
with st.sidebar:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/1018/1018524.png", width=100)
    
    st.markdown("<h3 style='text-align: center; color: #2C3E50;'>Habitat Futuro</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 0.8rem; color: gray;'>Agente AI 24/7</p>", unsafe_allow_html=True)
    
    st.divider()
    
    with st.expander("⚙️ Configuración Técnica"):
        if not api_key:
            api_key = st.text_input("Google API Key", type="password")
            if not api_key:
                st.warning("🔒 Clave necesaria")
        else:
            st.success("Licencia activa")

    with st.expander("🔐 Área Privada (Dueños)"):
        admin_pass = st.text_input("Contraseña", type="password", key="admin_pass")
        
        if admin_pass == "admin123":
            st.success("Acceso Admin OK")
            if os.path.exists("leads_inmobiliaria.csv"):
                try:
                    df = pd.read_csv("leads_inmobiliaria.csv")
                    st.caption(f"Total Clientes: {len(df)}")
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Descargar CRM", csv, "clientes.csv", "text/csv")
                    
                    # Vista previa más completa para debug
                    cols_a_mostrar = [c for c in df.columns if c in ["Nombre", "Teléfono", "Reunión/Visita", "Interés"]]
                    st.dataframe(df[cols_a_mostrar].tail(3), hide_index=True)
                    
                except Exception as e:
                    st.error("Error BD")
                    if st.button("Reiniciar BD"):
                        os.remove("leads_inmobiliaria.csv")
                        st.rerun()
            else:
                st.info("Sin datos aún.")
        elif admin_pass:
            st.error("Acceso denegado")

# --- LÓGICA INTELIGENTE DE CONEXIÓN (LISTA AMPLIADA) ---

def seleccionar_modelo_activo(api_key):
    # Probamos TODAS las variantes posibles
    candidatos = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-002",
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro",
        "gemini-1.5-pro-001",
        "gemini-1.5-pro-002",
        "gemini-1.5-pro-latest",
        "gemini-pro",
        "gemini-1.0-pro",
        "gemini-2.0-flash-exp" # Último recurso (experimental)
    ]
    
    for modelo in candidatos:
        try:
            tester = ChatGoogleGenerativeAI(model=modelo, google_api_key=api_key)
            tester.invoke("test") 
            return modelo
        except:
            continue
    # Si falla todo, devolvemos gemini-pro que suele ser el más estable en cuentas viejas
    return "gemini-pro"

def extraer_datos_cliente(texto_usuario, llm):
    fecha_hoy_txt, anio_actual = obtener_fecha_en_espanol()
    
    prompt_extraccion = [
        SystemMessage(content=f"""
        ERES UN MOTOR DE EXTRACCIÓN DE DATOS CRM.
        CONTEXTO TEMPORAL: Hoy es {fecha_hoy_txt}. Año: {anio_actual}.
        
        INVENTARIO:
        {INVENTARIO_REAL}
        
        TU MISIÓN:
        Analiza el texto del usuario y devuelve UNA sola línea con 4 campos separados por tuberías (|):
        NOMBRE | TELEFONO | CITA_COMPLETA | INTERES
        
        EJEMPLOS DE ENTRENAMIENTO (ÚSALOS COMO GUÍA):
        
        Usuario: "Hola, soy Ana, mi movil es 600112233 y quiero ver el ático mañana a las 5"
        Tu respuesta: Ana | 600112233 | {anio_actual}-MM-DD 17:00 | REF-001
        
        Usuario: "Me interesa el piso de chamberi, llamame al 911223344"
        Tu respuesta: SKIP | 911223344 | SKIP | REF-002
        
        Usuario: "Quiero cita para el loft el martes 20 por la tarde. Soy Carlos."
        Tu respuesta: Carlos | SKIP | 20/MM/{anio_actual} (Tarde) | REF-003
        
        REGLAS:
        1. Separador OBLIGATORIO: |
        2. Si falta un dato, pon: SKIP
        3. Para INTERES, usa SIEMPRE el código (REF-XXX). Si no sabes cual es, pon GENERAL.
        4. Para CITA_COMPLETA, calcula la fecha exacta basándote en que hoy es {fecha_hoy_txt}.
        """),
        HumanMessage(content=f"Analiza esto ahora mismo: '{texto_usuario}'")
    ]
    try:
        respuesta = llm.invoke(prompt_extraccion).content.strip()
        respuesta = respuesta.replace("\n", "").replace('"', '').replace("'", "")
        
        partes = respuesta.split("|")
        while len(partes) < 4:
            partes.append("SKIP")
            
        return {
            "Nombre": partes[0].strip(),
            "Teléfono": partes[1].strip(),
            "Reunión/Visita": partes[2].strip(),
            "Interés": partes[3].strip() 
        }
    except Exception as e:
        return {
            "Nombre": "SKIP",
            "Teléfono": "SKIP",
            "Reunión/Visita": "SKIP",
            "Interés": "SKIP"
        }

def guardar_lead(texto_usuario, llm):
    palabras_clave = ["@","correo", "mail", "llamame", "tlf", "telefono", "teléfono", "6", "visita", "verlo", "cita", "cambiar", "mejor el", "puedo el", "quedamos", "reunión", "a las"]
    tiene_numero = any(char.isdigit() for char in texto_usuario if len(texto_usuario) > 5)
    
    if any(keyword in texto_usuario.lower() for keyword in palabras_clave) or tiene_numero:
        
        datos_nuevos = extraer_datos_cliente(texto_usuario, llm)
        session_id = st.session_state.session_id
        file_path = "leads_inmobiliaria.csv"
        columnas = ["ID_Sesion", "Fecha_Registro", "Nombre", "Teléfono", "Reunión/Visita", "Interés"]
        
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                df = df[[c for c in df.columns if c in columnas or c == "ID_Sesion"]]
                for col in columnas:
                    if col not in df.columns: df[col] = "" 
            except:
                df = pd.DataFrame(columns=columnas)
        else:
            df = pd.DataFrame(columns=columnas)

        # LÓGICA FUSIÓN
        indice_usuario = None
        if session_id in df["ID_Sesion"].values:
            indice_usuario = df.index[df["ID_Sesion"] == session_id][0]
        elif datos_nuevos["Teléfono"] != "SKIP":
            tel_actual = str(datos_nuevos["Teléfono"]).replace(" ", "").replace("-", "")
            for idx, row in df.iterrows():
                tel_db = str(row["Teléfono"]).replace(" ", "").replace("-", "")
                if tel_actual in tel_db and len(tel_actual) > 6:
                    indice_usuario = idx
                    df.at[idx, "ID_Sesion"] = session_id
                    break

        # GUARDAR
        if indice_usuario is not None:
            cambios = False
            for campo in ["Nombre", "Teléfono", "Reunión/Visita", "Interés"]:
                dato = datos_nuevos[campo]
                if dato != "SKIP" and dato != "No especificado":
                    df.at[indice_usuario, campo] = dato
                    cambios = True
            
            if cambios:
                df.at[indice_usuario, "Fecha_Registro"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.toast("✅ Ficha actualizada", icon="🔄")
        else:
            if datos_nuevos["Teléfono"] != "SKIP" or datos_nuevos["Nombre"] != "SKIP":
                datos_limpios = {k: (v if v != "SKIP" else "Pendiente") for k, v in datos_nuevos.items()}
                nuevo_registro = {
                    "ID_Sesion": session_id,
                    "Fecha_Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    **datos_limpios
                }
                df = pd.concat([df, pd.DataFrame([nuevo_registro])], ignore_index=True)
                st.toast("✨ Nuevo cliente registrado", icon="👤")
            
        df.to_csv(file_path, index=False)
        return True
    return False

# --- INTERFAZ PRINCIPAL ---

st.markdown('<h1 class="hero-title">Habitat Futuro</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Encuentra tu hogar ideal en el corazón de la ciudad</p>', unsafe_allow_html=True)

if not api_key:
    st.info("👈 Por favor, inicia sesión con la clave API en el menú lateral.")
    st.stop()

if "modelo_seleccionado" not in st.session_state:
    with st.spinner("Conectando con el servidor..."):
        st.session_state.modelo_seleccionado = seleccionar_modelo_activo(api_key)

try:
    llm = ChatGoogleGenerativeAI(
        model=st.session_state.modelo_seleccionado, 
        google_api_key=api_key, 
        temperature=0.4
    )
except Exception as e:
    st.error("Error de conexión. Verifica la API Key.")
    st.info(f"Detalle: {e}")
    st.stop()

# Historial
fecha_hoy_txt, anio_actual = obtener_fecha_en_espanol()

if "messages" not in st.session_state:
    st.session_state.messages = [
        SystemMessage(content=f"""
        CONTEXTO: Hoy es {fecha_hoy_txt}.
        Eres 'Sara', la asesora comercial senior de 'Habitat Futuro'.
        
        INVENTARIO:
        {INVENTARIO_REAL}
        
        OBJETIVO: Conseguir agendar visita. Pide NOMBRE, TELÉFONO y FECHA/HORA preferida.
        """)
    ]

for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.write(msg.content)
    elif isinstance(msg, AIMessage):
        with st.chat_message("assistant", avatar="👩‍💼"):
            st.write(msg.content)

if prompt := st.chat_input("Estoy buscando..."):
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.messages.append(HumanMessage(content=prompt))

    guardar_lead(prompt, llm)
    
    with st.chat_message("assistant", avatar="👩‍💼"):
        message_placeholder = st.empty()
        try:
            ai_response = llm.invoke(st.session_state.messages)
            response_text = ai_response.content
            message_placeholder.markdown(response_text)
            st.session_state.messages.append(AIMessage(content=response_text))
        except Exception as e:
            st.error(f"Error: {e}")