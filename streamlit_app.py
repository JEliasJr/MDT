import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt

# --- CONFIGURAÇÃO DA PÁGINA ---
# Esta deve ser sempre a primeira linha de comando Streamlit
st.set_page_config(page_title="Simulador EPE - NT 037/2011", layout="wide")

# --- CONTROLE DE TEMA (MODO ESCURO/CLARO) ---
with st.sidebar:
    st.header("🎨 Aparência")
    # Toggle para trocar o tema (Padrão: Escuro)
    use_dark_mode = st.toggle("Modo Escuro", value=True)

# Define as cores baseadas na escolha
if use_dark_mode:
    theme_plotly = "plotly_dark"
    bg_color = "#0e1117"
    txt_color = "#ffffff"
    card_color = "#262730"
else:
    theme_plotly = "plotly_white"
    bg_color = "#ffffff"
    txt_color = "#000000"
    card_color = "#f0f2f6"

# CSS para forçar a mudança visual na interface inteira
st.markdown(f'''
    <style>
    .stApp {{
        background-color: {bg_color};
        color: {txt_color};
    }}
    /* Forçar cor dos inputs para garantir leitura */
    input, .stNumberInput input {{
        color: {txt_color} !important;
    }}
    /* Cor das abas */
    .stTabs [data-baseweb="tab-list"] button {{
        color: {txt_color};
    }}
    </style>
''', unsafe_allow_html=True)

# --- TÍTULO DO APP ---
st.title("⚡ Modelagem de Turbina Hidráulica (EPE)")
st.markdown("Ferramenta baseada na **Nota Técnica EPE-DEE-RE-037/2011-r2**.")

# --- BARRA LATERAL: PARÂMETROS ---
with st.sidebar:
    st.header("⚙️ Parâmetros")
    
    with st.expander("1. Coeficientes da Turbina", expanded=True):
        st.caption("Polinômio (Eq. 3): η = a00 + ...")
        a00 = st.number_input("a00", value=-45.0, format="%.4f")
        a10 = st.number_input("a10 (h)", value=1.8, format="%.4f")
        a01 = st.number_input("a01 (q)", value=1.2, format="%.4f")
        a20 = st.number_input("a20 (h²)", value=-0.012, format="%.5f")
        a02 = st.number_input("a02 (q²)", value=-0.004, format="%.5f")
        a11 = st.number_input("a11 (h*q)", value=0.001, format="%.5f")
    
    with st.expander("2. Limites Operativos", expanded=True):
        h_nom = st.number_input("Queda Nominal (m)", value=80.0)
        q_min = st.number_input("Vazão Mín/Unid (m³/s)", value=20.0)
        q_max = st.number_input("Vazão Máx/Unid (m³/s)", value=150.0)
        n_maquinas = st.slider("Nº Máquinas", 1, 20, 6)
        rend_gerador = st.number_input("Rendimento Gerador (%)", value=98.0)

# --- FUNÇÃO PRINCIPAL DA CURVA ---
def curva_colina(h, q):
    eta = (a02 * q**2) + (a20 * h**2) + (a11 * q * h) + (a01 * q) + (a10 * h) + a00
    return np.clip(eta, 0, 100)

# --- ESTRUTURA DE ABAS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 3D Interativo", 
    "📊 2D Interativo", 
    "⚙️ Otimização Despacho", 
    "📑 Cálculo de Médias",
    "📐 Fórmulas (EPE)"
])

# --- ABA 1: 3D ---
with tab1:
    st.subheader("Superfície 3D (Hill Chart)")
    h_vals = np.linspace(h_nom * 0.5, h_nom * 1.5, 50)
    q_vals = np.linspace(q_min, q_max, 50)
    H, Q = np.meshgrid(h_vals, q_vals)
    Z = curva_colina(H, Q)
    
    fig = go.Figure(data=[go.Surface(z=Z, x=H, y=Q, colorscale='Viridis', opacity=0.9)])
    fig.update_layout(
        scene=dict(xaxis_title='Queda (m)', yaxis_title='Vazão (m³/s)', zaxis_title='Eficiência (%)'),
        margin=dict(l=0, r=0, b=0, t=0), height=600, 
        template=theme_plotly # Tema dinâmico
    )
    st.plotly_chart(fig, use_container_width=True)

# --- ABA 2: 2D ---
with tab2:
    st.subheader("Diagrama de Contorno")
    col1, col2 = st.columns([3, 1])
    with col1:
        h_2d = np.linspace(h_nom * 0.6, h_nom * 1.4, 100)
        q_2d = np.linspace(q_min, q_max, 100)
        fig_2d = go.Figure(data=go.Contour(
            z=curva_colina(*np.meshgrid(h_2d, q_2d)), x=h_2d, y=q_2d, colorscale='Viridis',
            contours=dict(coloring='heatmap', showlabels=True, labelfont=dict(color=txt_color)),
            colorbar=dict(title='η (%)')
        ))
        fig_2d.update_layout(
            xaxis_title="Queda (m)", yaxis_title="Vazão (m³/s)", 
            template=theme_plotly, height=600
        )
        st.plotly_chart(fig_2d, use_container_width=True)
    with col2:
        st.info("Simule um ponto:")
        h_t = st.number_input("H (m)", value=h_nom, key="h2d")
        q_t = st.number_input("Q (m³/s)", value=(q_min+q_max)/2, key="q2d")
        st.metric("Rendimento", f"{curva_colina(h_t, q_t):.2f}%")

# --- ABA 3: DESPACHO ---
with tab3:
    st.subheader("Simulação de Despacho Ótimo")
    c1, c2 = st.columns(2)
    h_sim = c1.number_input("Queda Disponível (m)", value=80.0)
    q_tot_sim = c2.number_input("Vazão Total (m³/s)", value=300.0)
    
    if st.button("🚀 Otimizar"):
        res = []
        best_p = -1
        for i in range(1, n_maquinas + 1):
            q_u = q_tot_sim / i
            if q_u < q_min: status, rend = "Inviável", 0
            elif q_u > q_max: status, rend = "Limitado", curva_colina(h_sim, q_max)
            else: status, rend = "Viável", curva_colina(h_sim, q_u)
            
            pot = i * (rend/100) * 9.81 * h_sim * min(q_u, q_max) / 1000
            res.append({"Máq": i, "Q/Unid": f"{q_u:.1f}", "η (%)": f"{rend:.1f}", "Pot (MW)": round(pot, 2), "Status": status})
            if status != "Inviável" and pot > best_p: best_p = pot
        st.dataframe(pd.DataFrame(res).style.highlight_max(axis=0, subset=["Pot (MW)"], color='green'))

# --- ABA 4: MÉDIAS ---
with tab4:
    st.subheader("Cálculo de Parâmetros Médios")
    up = st.file_uploader("Upload CSV (Colunas: Queda, Vazao)", type="csv")
    if up:
        df = pd.read_csv(up)
        if {'Queda', 'Vazao'}.issubset(df.columns):
            df['Rend_Otimo'] = df.apply(lambda r: curva_colina(r['Queda'], r['Vazao']/n_maquinas), axis=1)
            
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(y=df['Rend_Otimo'], mode='lines', name='Rendimento'))
            fig_line.update_layout(title="Série Histórica", template=theme_plotly)
            st.plotly_chart(fig_line, use_container_width=True)
        else: st.error("CSV inválido.")

# --- ABA 5: FÓRMULAS ---
with tab5:
    st.header("📐 Documentação Matemática (NT 037/2011-r2)")
    st.divider()
    
    col_eq1, col_eq2 = st.columns(2)
    with col_eq1:
        st.subheader("1. Rendimento da Turbina (Eq. 3)")
        st.latex(r'''\\eta_{t}(h,q) = a_{02}q^{2} + a_{20}h^{2} + a_{11}qh + a_{01}q + a_{10}h + a_{00}''')
        st.subheader("2. Problema de Otimização (Eq. 6)")
        st.latex(r'''\\text{Max } P_{tot} = \\sum_{i=1}^{n} (\\eta_t(h, q_i) \\cdot q_i \\cdot h \\cdot \\rho \\cdot g)''')
    with col_eq2:
        st.subheader("3. Perda Hidráulica (Eq. 1 e 15)")
        st.latex(r'''\\Delta h_{med} = \\frac{\\sum (E_m \\cdot \\Delta h_m)}{\\sum E_m}''')
        st.subheader("4. Rendimento Médio (Eq. 2)")
        st.latex(r'''\\eta_{med} = \\frac{\\sum_{m=1}^{N} (E_m \\cdot \\eta_{conj,m})}{\\sum_{m=1}^{N} E_m}''')
        st.latex(r'''\\eta_{conj} = \\eta_t \\times \\eta_g''')
