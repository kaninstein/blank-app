import ccxt
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Gráfico de Velas Binance com Hilo Activator Stairs", layout="wide")
st.title("Gráfico de Velas Binance (Testnet) com Hilo Activator Stairs")

@st.cache_data(ttl=3600)
def get_binance_data(symbol, timeframe, limit):
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future'
        }
    })
    exchange.set_sandbox_mode(True)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def hilo_activator_stairs(df, period=8, shift=1, exp=False):
    if exp:
        max_val = df['high'].shift(shift).ewm(span=period).mean()
        min_val = df['low'].shift(shift).ewm(span=period).mean()
    else:
        max_val = df['high'].shift(shift).rolling(window=period).mean()
        min_val = df['low'].shift(shift).rolling(window=period).mean()
    
    pos = np.where(df['close'] > max_val, -1, np.where(df['close'] < min_val, 1, 0))
    pos = pd.Series(pos).replace(to_replace=0, method='ffill')
    hilo = np.where(pos == 1, max_val, min_val)
    
    return pd.Series(hilo, name='hilo'), pd.Series(pos, name='position')

st.sidebar.header("Configurações")
symbol = st.sidebar.selectbox("Selecione o par", ["BTC/USDT", "ETH/USDT", "BNB/USDT"])
timeframe = st.sidebar.selectbox("Selecione o timeframe", ["1m", "5m", "15m", "1h", "4h", "1d"])
limit = st.sidebar.slider("Número de candles", min_value=50, max_value=1000, value=120)
period = st.sidebar.slider("Período do Hilo Activator", min_value=2, max_value=50, value=8)
shift = st.sidebar.slider("Deslocamento do Hilo Activator", min_value=0, max_value=10, value=1)
exp = st.sidebar.checkbox("Usar média móvel exponencial", value=False)

df = get_binance_data(symbol, timeframe, limit)
df['hilo'], df['position'] = hilo_activator_stairs(df, period, shift, exp)

# Calcular a largura das velas de forma mais robusta
df['timestamp_diff'] = df['timestamp'].diff().dt.total_seconds()
default_width = df['timestamp_diff'].median() * 0.8  # Use a mediana como valor padrão
df['candle_width'] = df['timestamp_diff'].fillna(default_width) * 0.8

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])

fig.add_trace(go.Candlestick(x=df['timestamp'],
                             open=df['open'],
                             high=df['high'],
                             low=df['low'],
                             close=df['close'],
                             name='OHLC'),
              row=1, col=1)

# Adicionar Hilo Activator Stairs
for i in range(len(df)):
    if pd.notna(df['hilo'].iloc[i]) and pd.notna(df['candle_width'].iloc[i]):
        y_position = df['hilo'].iloc[i]
        color = "red" if df['position'].iloc[i] == 1 else "green"
        half_width = pd.Timedelta(seconds=df['candle_width'].iloc[i]/2)
        fig.add_shape(type="line",
                      x0=df['timestamp'].iloc[i] - half_width,
                      x1=df['timestamp'].iloc[i] + half_width,
                      y0=y_position, y1=y_position,
                      line=dict(color=color, width=2),
                      row=1, col=1)

fig.add_trace(go.Bar(x=df['timestamp'], y=df['volume'], name='Volume', marker_color='rgba(0,0,0,0.5)'),
              row=2, col=1)

fig.update_layout(
    title=f'{symbol} - Gráfico de Velas com Hilo Activator Stairs',
    yaxis_title='Preço',
    xaxis_rangeslider_visible=False,
    height=800,
    showlegend=False
)

fig.update_yaxes(title_text="Volume", row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

if st.checkbox("Mostrar dados brutos"):
    st.write(df)