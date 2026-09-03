import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Analisador Técnico B3",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Analisador Técnico para Swing Trade - B3")
st.markdown("Monitoramento automático de indicadores de Análise Técnica.")

# Painel Lateral - Seleção das Ações
st.sidebar.header("Configurações")
acoes_disponiveis = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBAS3.SA", "WEGE3.SA"]
acao_selecionada = st.sidebar.selectbox("Escolha uma ação:", acoes_disponiveis)

periodo = st.sidebar.selectbox("Período do Gráfico:", ["6m", "1y", "2y"], index=1)

# Função para buscar e processar os dados
@st.cache_data(ttl=3600)
def carregar_dados(ticker, periodo_tempo):
    df = yf.download(ticker, period=periodo_tempo, interval="1d")
    
    # Ajuste de colunas caso venham formatadas com MultiIndex pelo yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # Cálculo das Médias Móveis
    df['MMA_9'] = ta.sma(df['Close'], length=9)
    df['MMA_21'] = ta.sma(df['Close'], length=21)
    
    # Cálculo do IFR (Índice de Força Relativa)
    df['IFR_14'] = ta.rsi(df['Close'], length=14)
    
    # Cálculo das Bandas de Bollinger
    bollinger = ta.bbands(df['Close'], length=20, std=2)
    if bollinger is not None and not bollinger.empty:
        df['BBL_20'] = bollinger.iloc[:, 0]  # Banda Inferior
        df['BBU_20'] = bollinger.iloc[:, 2]  # Banda Superior
        
    return df

with st.spinner("Carregando dados da B3..."):
    df = carregar_dados(acao_selecionada, periodo)

# Últimas cotações e indicadores
ultimo_preco = float(df['Close'].iloc[-1])
preco_anterior = float(df['Close'].iloc[-2])
variacao = ((ultimo_preco - preco_anterior) / preco_anterior) * 100

ultimo_ifr = float(df['IFR_14'].iloc[-1])
mma9_atual = float(df['MMA_9'].iloc[-1])
mma21_atual = float(df['MMA_21'].iloc[-1])

# Métricas no topo da tela
col1, col2, col3, col4 = st.columns(4)
col1.metric("Preço Atual", f"R$ {ultimo_preco:.2f}", f"{variacao:.2f}%")
col2.metric("IFR (14)", f"{ultimo_ifr:.1f}")
col3.metric("Média Móvel 9d", f"R$ {mma9_atual:.2f}")
col4.metric("Média Móvel 21d", f"R$ {mma21_atual:.2f}")

st.markdown("---")

# Construção do Gráfico Interativo com Plotly (Preço + IFR)
fig = make_subplots(
    rows=2, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.05, 
    row_heights=[0.7, 0.3],
    subplot_titles=(f"Gráfico Candlestick: {acao_selecionada}", "Indicador IFR (14)")
)

# 1. Candlesticks (Preço)
fig.add_trace(go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'],
    low=df['Low'], close=df['Close'], name="Preço"
), row=1, col=1)

# 2. Médias Móveis
fig.add_trace(go.Scatter(x=df.index, y=df['MMA_9'], line=dict(color='orange', width=1.5), name='MMA 9 (Rápida)'), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['MMA_21'], line=dict(color='blue', width=2), name='MMA 21 (Lenta)'), row=1, col=1)

# 3. Bandas de Bollinger
if 'BBL_20' in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df['BBU_20'], line=dict(color='gray', width=1, dash='dash'), name='Banda Sup.'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BBL_20'], line=dict(color='gray', width=1, dash='dash'), name='Banda Inf.'), row=1, col=1)

# 4. Painel Inferior: IFR
fig.add_trace(go.Scatter(x=df.index, y=df['IFR_14'], line=dict(color='purple', width=2), name='IFR 14'), row=2, col=1)

# Linhas de referência de sobrecompra e sobrevenda
fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

fig.update_layout(height=650, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# Módulo de Análise e Sinais
st.subheader("📋 Resumo da Análise Técnica")

sinais = []

# Checagem de Médias Móveis
if mma9_atual > mma21_atual:
    sinais.append("🟢 **Tendência de Curto Prazo:** Alta (Média móvel de 9 dias acima da média de 21 dias).")
else:
    sinais.append("🔴 **Tendência de Curto Prazo:** Baixa (Média móvel de 9 dias abaixo da média de 21 dias).")

# Checagem de IFR
if ultimo_ifr <= 30:
    sinais.append("🟢 **IFR Sobrevendido (<=30):** O ativo está em zona de desconto. Pode indicar **oportunidade de compra** ou repique.")
elif ultimo_ifr >= 70:
    sinais.append("🔴 **IFR Sobrecomprado (>=70):** O ativo está esticado no curto prazo. **Risco elevado** para novas compras.")
else:
    sinais.append("⚪ **IFR Neutro:** O indicador está em região intermediária.")

for sinal in sinais:
    st.write(sinal)
