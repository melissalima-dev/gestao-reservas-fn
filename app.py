import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse
from datetime import date
import io

# Configuração da página e identidade visual FN
st.set_page_config(page_title="GESTOR DE RESERVAS - FN DISTRIBUIDORA", page_icon="🏢", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; }
    .stButton>button[kind="primary"] {
        background-color: #F59E0B;
        color: #0F172A;
        border: none;
        font-weight: bold;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #D97706;
        color: #FFFFFF;
    }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #0284C7;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .fn-header {
        display: flex;
        align-items: center;
        gap: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid #0284C7;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Conexão com PostgreSQL (Supabase) segura
@st.cache_resource
def get_engine():
    try:
        if "DATABASE_URL" in st.secrets:
            return create_engine(st.secrets["DATABASE_URL"])
    except Exception:
        pass
    return None

engine = get_engine()

# --- SISTEMA DE LOGIN ---
USUARIOS_PADRAO = {
    "distribuicao.fndistribuidora@gmail.com": {"senha": "#Fn123", "perfil": "Admin"},
    "fiscal@fndistribuidora.com.br": {"senha": "123", "perfil": "Fiscal"},
    "distribuicao@fndistribuidora.com.br": {"senha": "123", "perfil": "Distribuicao"},
}

if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario = ""

if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='color: #0284C7; text-align: center;'>FN DISTRIBUIDORA</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: #64748B;'>GESTÃO DE RESERVAS</h3><br>", unsafe_allow_html=True)
        
        if engine is None:
            st.error("⚠️ Erro de configuração: A variável DATABASE_URL não foi encontrada nos Secrets do Streamlit.")
        
        email = st.text_input("E-mail corporativo")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar no Sistema", type="primary", use_container_width=True):
            if email in USUARIOS_PADRAO and USUARIOS_PADRAO[email]["senha"] == senha:
                st.session_state.logado = True
                st.session_state.usuario = email
                st.rerun()
            else:
                st.error("E-mail ou senha inválidos.")
    st.stop()

# --- CABEÇALHO COM IDENTIDADE VISUAL ---
st.markdown("""
    <div class="fn-header">
        <h2 style="color: #0284C7; margin: 0;">FN DISTRIBUIDORA</h2>
        <span style="background-color: #F59E0B; color: #0F172A; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 14px;">GESTÃO DE RESERVAS</span>
    </div>
""", unsafe_allow_html=True)

col_info, col_logout = st.columns([4, 1])
with col_info:
    st.caption(f"Logado como: **{st.session_state.usuario}**")
with col_logout:
    if st.button("🚪 Sair"):
        st.session_state.logado = False
        st.rerun()

def carregar_tabela(nome_tabela):
    try:
        if engine:
            return pd.read_sql(f"SELECT * FROM {nome_tabela}", engine)
    except Exception:
        pass
    return pd.DataFrame()

df_hoteis = carregar_tabela("hoteis")
df_motoristas = carregar_tabela("motoristas")
df_reservas = carregar_tabela("reservas")

st.success("✅ Sistema ligado com sucesso ao banco de dados!")
st.dataframe(df_reservas, use_container_width=True)
