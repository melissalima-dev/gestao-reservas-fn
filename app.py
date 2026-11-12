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
    /* Cores inspiradas na identidade visual da FN Distribuidora (Azul FN e Amarelo Dourado) */
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

# Conexão com PostgreSQL (Supabase)
@st.cache_resource
def get_engine():
    return create_engine(st.secrets["DATABASE_URL"])

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
    if st.button("🚪 Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

# Carregar dados do PostgreSQL
def carregar_tabela(nome_tabela):
    try:
        return pd.read_sql(f"SELECT * FROM {nome_tabela}", engine)
    except Exception:
        return pd.DataFrame()

df_hoteis = carregar_tabela("hoteis")
df_motoristas = carregar_tabela("motoristas")
df_reservas = carregar_tabela("reservas")

# --- ABAS DO SISTEMA ---
aba_reservas, aba_hoteis, aba_motoristas, aba_dashboard = st.tabs([
    "📅 Nova Solicitação & Histórico", "🏨 Hotéis", "🚛 Motoristas", "📊 Dashboard & Relatórios"
])

# ==========================================
# ABA 1: RESERVAS E HISTÓRICO DETALHADO
# ==========================================
with aba_reservas:
    col_form, col_resumo = st.columns([1.3, 1])

    with col_form:
        st.subheader("📝 Nova Solicitação de Reserva")
        c1, c2 = st.columns(2)
        checkin = c1.date_input("Check-in", value=date.today())
        checkout = c2.date_input("Check-out", value=date.today())
        diarias = max((checkout - checkin).days, 1)

        cidades = sorted(df_hoteis["cidade"].dropna().unique().tolist()) if not df_hoteis.empty else []
        cidade_sel = st.selectbox("Cidade", ["Selecione..."] + cidades)

        hoteis_filtrados = df_hoteis[df_hoteis["cidade"] == cidade_sel] if cidade_sel != "Selecione..." else pd.DataFrame()
        lista_hoteis = hoteis_filtrados["nome"].tolist() if not hoteis_filtrados.empty and "nome" in hoteis_filtrados.columns else []
        hotel_sel = st.selectbox("Hotel", ["Selecione..."] + lista_hoteis)

        lista_mot = sorted(df_motoristas["nome"].dropna().unique().tolist()) if not df_motoristas.empty and "nome" in df_motoristas.columns else []
        h1, h2 = st.columns(2)
        hosp1 = h1.selectbox("Hóspede 1 (Motorista)", ["Selecione..."] + lista_mot)
        hosp2 = h2.selectbox("Hóspede 2 (Opcional)", ["Nenhum (quarto individual)"] + lista_mot)

        tipo_quarto = "Individual" if hosp2 == "Nenhum (quarto individual)" else "Duplo"

        # Puxa valor base e permite alteração flexível
        valor_base = 130.0 if tipo_quarto == "Individual" else 260.0
        pix_hotel = ""
        if hotel_sel != "Selecione..." and not hoteis_filtrados.empty:
            dados_h = hoteis_filtrados[hoteis_filtrados["nome"] == hotel_sel].iloc[0]
            col_val = "valor_individual" if tipo_quarto == "Individual" else "valor_duplo"
            if col_val in dados_h and pd.notna(dados_h[col_val]):
                valor_base = float(dados_h[col_val])
            if "pix" in dados_h and pd.notna(dados_h["pix"]):
                pix_hotel = str(dados_h["pix"])

        valor_pernoite = st.number_input("Valor da Pernoite (R$ - Ajustável)", min_value=0.0, value=valor_base, step=5.0)

        p1, p2, p3 = st.columns(3)
        pagamento = p1.selectbox("Pagamento", [
            "AGUARDANDO NF", "AGUARDANDO PAGAMENTO", "PAGAMENTO MENSAL", "PAGAMENTO SEMANAL", "PAGO"
        ])
        numero_nf = p2.text_input("Número da NF")
        status = p3.selectbox("Status", ["AGUARDANDO", "RESERVADO"])

    with col_resumo:
        st.subheader("💰 Budget & WhatsApp")
        budget_diaria = 130.0 if tipo_quarto == "Individual" else 260.0
        valor_total = valor_pernoite * diarias
        budget_total = budget_diaria * diarias

        b1, b2, b3 = st.columns(3)
        b1.metric("Diárias", diarias)
        b2.metric("Quarto", tipo_quarto)
        b3.metric("Valor Total", f"R$ {valor_total:,.2f}")

        if valor_total <= budget_total:
            st.success(f"Dentro do Budget (Limite: R$ {budget_total:,.2f})")
        else:
            st.warning(f"Acima do Budget em R$ {valor_total - budget_total:,.2f}")

        texto_h2 = "NENHUM" if hosp2 == "Nenhum (quarto individual)" else hosp2
        msg_whats = (
            f"Olá, equipe do {hotel_sel}! Tudo bem?\n\n"
            f"Gostaria de solicitar a reserva para os nossos colaboradores:\n"
            f"- Hóspede 1: {hosp1}\n"
            f"- Hóspede 2: {texto_h2}\n"
            f"- Quarto: {tipo_quarto}\n"
            f"Período: {checkin.strftime('%d/%m/%Y')} a {checkout.strftime('%d/%m/%Y')} ({diarias} diária(s))\n\n"
            f"O valor da diária segue o acordo de R$ {valor_pernoite:,.2f}? A chave PIX cadastrada ainda é {pix_hotel}?\n\n"
            f"Aguardo retorno para confirmarmos!"
        )
        msg_editada = st.text_area("Mensagem pronta para WhatsApp", value=msg_whats, height=180)

        if st.button("💾 Salvar Solicitação no Banco", type="primary", use_container_width=True):
            if cidade_sel == "Selecione..." or hotel_sel == "Selecione..." or hosp1 == "Selecione...":
                st.error("Preencha Cidade, Hotel e Hóspede 1 antes de salvar.")
            else:
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO reservas (check_in, check_out, cidade, hotel, hospede_1, hospede_2, quarto, valor_total, pagamento, nf, status, pdf_nf, comprovante)
                        VALUES (:ci, :co, :cid, :hot, :h1, :h2, :qto, :val, :pag, :nf, :st, '', '')
                    """), {
                        "ci": str(checkin), "co": str(checkout), "cid": cidade_sel, "hot": hotel_sel,
                        "h1": hosp1, "h2": "" if hosp2 == "Nenhum (quarto individual)" else hosp2,
                        "qto": tipo_quarto, "val": valor_total, "pag": pagamento, "nf": numero_nf, "st": status
                    })
                st.success("Reserva salva com sucesso!")
                st.rerun()

        link_wa = f"https://wa.me/?text={urllib.parse.quote(msg_editada)}"
        st.link_button("📲 Abrir no WhatsApp", link_wa, use_container_width=True)

    st.divider()
    st.subheader("📋 Histórico Detalhado de Reservas Salvas")

    if not df_reservas.empty:
        # Filtros e Pesquisa Avançada
        f1, f2, f3, f4 = st.columns(4)
        busca = f1.text_input("🔍 Pesquisar geral (Hotel, Cidade, Hóspede, NF)")
        filtro_status = f2.multiselect("Filtrar Status", ["AGUARDANDO", "RESERVADO"])
        filtro_pag = f3.multiselect("Filtrar Pagamento", [
            "AGUARDANDO NF", "AGUARDANDO PAGAMENTO", "PAGAMENTO MENSAL", "PAGAMENTO SEMANAL", "PAGO"
        ])
        
        df_view = df_reservas.copy()
        if busca:
            mask = df_view.astype(str).apply(lambda x: x.str.contains(busca, case=False, na=False)).any(axis=1)
            df_view = df_view[mask]
        if filtro_status and "status" in df_view.columns:
            df_view = df_view[df_view["status"].isin(filtro_status)]
        if filtro_pag and "pagamento" in df_view.columns:
            df_view = df_view[df_view["pagamento"].isin(filtro_pag)]

        # Tabela totalmente editável com colunas separadas
        df_editado = st.data_editor(
            df_view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "check_in": "Check-in",
                "check_out": "Check-out",
                "cidade": "Cidade",
                "hotel": "Hotel",
                "hospede_1": "Hóspede 1",
                "hospede_2": "Hóspede 2",
                "quarto": st.column_config.SelectboxColumn("Quarto", options=["Individual", "Duplo"]),
                "valor_total": st.column_config.NumberColumn("Valor Total (R$)", format="R$ %.2f"),
                "pagamento": st.column_config.SelectboxColumn("Pagamento", options=[
                    "AGUARDANDO NF", "AGUARDANDO PAGAMENTO", "PAGAMENTO MENSAL", "PAGAMENTO SEMANAL", "PAGO"
                ]),
                "nf": "Número da NF",
                "pdf_nf": "PDF da Nota Fiscal (Link/Obs)",
                "comprovante": "Comprovante Pagamento (Link/Obs)",
                "status": st.column_config.SelectboxColumn("Status", options=["AGUARDANDO", "RESERVADO"]),
            },
            key="editor_reservas_completo"
        )

        if st.button("💾 Salvar Alterações do Histórico no PostgreSQL", type="primary"):
            with engine.begin() as conn:
                for _, row in df_editado.iterrows():
                    if "id" in row:
                        conn.execute(text("""
                            UPDATE reservas
                            SET check_in = :ci, check_out = :co, cidade = :cid, hotel = :hot,
                                hospede_1 = :h1, hospede_2 = :h2, quarto = :qto,
                                valor_total = :val, pagamento = :pag, nf = :nf, 
                                pdf_nf = :pdf, comprovante = :comp, status = :st
                            WHERE id = :id
                        """), {
                            "ci": row.get("check_in"), "co": row.get("check_out"), "cid": row.get("cidade"),
                            "hot": row.get("hotel"), "h1": row.get("hospede_1"), "h2": row.get("hospede_2"),
                            "qto": row.get("quarto"), "val": row.get("valor_total"), "pag": row.get("pagamento"),
                            "nf": row.get("nf"), "pdf": row.get("pdf_nf", ""), "comp": row.get("comprovante", ""),
                            "st": row.get("status"), "id": row["id"]
                        })
            st.success("Modificações salvas com sucesso no banco de dados!")
            st.rerun()
    else:
        st.info("Nenhuma reserva encontrada.")

# ==========================================
# ABA 2: HOTÉIS
# ==========================================
with aba_hoteis:
    st.subheader("🏨 Cadastro de Hotéis")
    with st.expander("➕ Adicionar Novo Hotel"):
        hc1, hc2, hc3, hc4 = st.columns(4)
        n_hotel = hc1.text_input("Nome do Hotel")
        n_cidade = hc2.text_input("Cidade")
        n_ind = hc3.number_input("Valor Individual Base (R$)", min_value=0.0, value=130.0)
        n_dup = hc4.number_input("Valor Duplo Base (R$)", min_value=0.0, value=260.0)
        n_pix = st.text_input("Chave PIX / Contato")
        if st.button("Salvar Cadastro do Hotel", type="primary"):
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO hoteis (nome, cidade, valor_individual, valor_duplo, pix)
                    VALUES (:n, :c, :vi, :vd, :p)
                """), {"n": n_hotel.upper(), "c": n_cidade.upper(), "vi": n_ind, "vd": n_dup, "p": n_pix})
            st.success("Hotel cadastrado com sucesso!")
            st.rerun()
    st.dataframe(df_hoteis, use_container_width=True, hide_index=True)

# ==========================================
# ABA 3: MOTORISTAS
# ==========================================
with aba_motoristas:
    st.subheader("🚛 Cadastro de Colaboradores (Equipe)")
    mc1, mc2, mc3 = st.columns([2, 1, 1])
    n_mot = mc1.text_input("Nome Completo do Colaborador")
    n_func = mc2.selectbox("Função", ["Motorista", "Ajudante"])
    if mc3.button("Cadastrar Colaborador", type="primary"):
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO motoristas (nome, funcao) VALUES (:n, :f)"), {
                "n": n_mot.upper(), "f": n_func
            })
        st.success("Colaborador cadastrado!")
        st.rerun()
    st.dataframe(df_motoristas, use_container_width=True, hide_index=True)

# ==========================================
# ABA 4: DASHBOARD & EXPORTAÇÃO EXCEL
# ==========================================
with aba_dashboard:
    st.subheader("📊 Dashboard & Análise Financeira")
    if not df_reservas.empty and "valor_total" in df_reservas.columns:
        df_reservas["valor_total"] = pd.to_numeric(df_reservas["valor_total"], errors="coerce").fillna(0)
        
        # Tenta extrair o mês/ano do check-in para o gráfico anual
        if "check_in" in df_reservas.columns:
            df_reservas["mes_ano"] = pd.to_datetime(df_reservas["check_in"], errors="coerce").dt.to_period("M").astype(str)
        else:
            df_reservas["mes_ano"] = "Indefinido"

        gasto_total = df_reservas["valor_total"].sum()
        qtd_res = len(df_reservas)

        d1, d2 = st.columns(2)
        d1.metric("Gasto Total Acumulado", f"R$ {gasto_total:,.2f}")
        d2.metric("Total de Reservas", qtd_res)

        st.markdown("### 📈 Gastos Mensais ao Longo do Ano")
        gasto_mensal = df_reservas.groupby("mes_ano")["valor_total"].sum().reset_index()
        st.bar_chart(gasto_mensal.set_index("mes_ano"))

        if "cidade" in df_reservas.columns:
            st.markdown("### 🏙️ Gastos por Cidade")
            st.bar_chart(df_reservas.groupby("cidade")["valor_total"].sum())

        # Botão de Exportação para Excel (.xlsx) contendo todas as colunas filtradas
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_view.to_excel(writer, index=False, sheet_name="Reservas Filtradas")
        
        st.download_button(
            label="📥 Exportar Período/Filtros Selecionados para Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name="relatorio_fn_reservas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    else:
        st.info("Sem dados suficientes para gerar os gráficos no momento.")
