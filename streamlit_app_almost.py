import ccxt
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Gráfico de Velas com Hilo Activator Stairs (Testnet)", layout="wide")
st.title("Gráfico de Velas com Hilo Activator Stairs (Testnet)")

# Lista de ativos com períodos específicos
assets = [
    {"id": 1, "ticker": "BTC/USDT", "period": 40},
    {"id": 2, "ticker": "ETH/USDT", "period": 23},
    {"id": 3, "ticker": "ADA/USDT", "period": 43},
    {"id": 4, "ticker": "NEO/USDT", "period": 30},
    {"id": 5, "ticker": "LINK/USDT", "period": 31},
    {"id": 6, "ticker": "MANA/USDT", "period": 52},
    {"id": 7, "ticker": "SUSHI/USDT", "period": 40},
    {"id": 8, "ticker": "ATOM/USDT", "period": 20},
    {"id": 9, "ticker": "FTM/USDT", "period": 52},
    {"id": 12, "ticker": "XRP/USDT", "period": 40},
    {"id": 13, "ticker": "SOL/USDT", "period": 38},
    {"id": 14, "ticker": "DOGE/USDT", "period": 42},
    {"id": 15, "ticker": "BNB/USDT", "period": 50},
    {"id": 16, "ticker": "LTC/USDT", "period": 33},
    {"id": 17, "ticker": "DOT/USDT", "period": 37},
    {"id": 18, "ticker": "AVAX/USDT", "period": 46},
    {"id": 20, "ticker": "MATIC/USDT", "period": 29},
    {"id": 21, "ticker": "AXS/USDT", "period": 32},
    {"id": 22, "ticker": "ALGO/USDT", "period": 27},
    {"id": 23, "ticker": "AAVE/USDT", "period": 35},
    {"id": 24, "ticker": "UNI/USDT", "period": 39},
    {"id": 25, "ticker": "FIL/USDT", "period": 34},
    {"id": 26, "ticker": "SAND/USDT", "period": 28},
    {"id": 27, "ticker": "CRV/USDT", "period": 41},
    {"id": 28, "ticker": "FTT/USDT", "period": 36},
    {"id": 29, "ticker": "VET/USDT", "period": 30},
    {"id": 30, "ticker": "THETA/USDT", "period": 31},
    {"id": 31, "ticker": "GALA/USDT", "period": 43}
]

@st.cache_data(ttl=3600)
def get_binance_testnet_data(symbol, timeframe, limit):
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future'
        }
    })
    exchange.set_sandbox_mode(True)
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv:
            raise ValueError(f"Nenhum dado disponível para {symbol}")
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        st.error(f"Erro ao obter dados para {symbol}: {str(e)}")
        return pd.DataFrame()

def hilo_activator_stairs(df, period, shift=1, exp=False):
    if df.empty:
        return pd.Series(dtype=float), pd.Series(dtype=int)
    
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
selected_asset = st.sidebar.selectbox("Selecione o ativo", [asset['ticker'] for asset in assets])
selected_asset_info = next(asset for asset in assets if asset['ticker'] == selected_asset)

period = st.sidebar.slider("Período do Hilo Activator", min_value=2, max_value=100, value=8)
timeframe = st.sidebar.selectbox("Timeframe", ["1d", "4h", "1h", "15m", "5m"], index=0)
limit = st.sidebar.slider("Número de candles", min_value=50, max_value=1000, value=120)
shift = st.sidebar.slider("Deslocamento do Hilo Activator", min_value=0, max_value=10, value=1)
exp = st.sidebar.checkbox("Usar média móvel exponencial", value=False)


df = get_binance_testnet_data(selected_asset, timeframe, limit)

if not df.empty:
    df['hilo'], df['position'] = hilo_activator_stairs(df, period, shift, exp)

    df['timestamp_diff'] = df['timestamp'].diff().dt.total_seconds()
    default_width = df['timestamp_diff'].median() * 0.8
    df['candle_width'] = df['timestamp_diff'].fillna(default_width) * 0.8

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])

    fig.add_trace(go.Candlestick(x=df['timestamp'],
                                 open=df['open'],
                                 high=df['high'],
                                 low=df['low'],
                                 close=df['close'],
                                 name='OHLC'),
                  row=1, col=1)

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
        title=f'{selected_asset} - Gráfico de Velas com Hilo Activator Stairs (Período: {period})',
        yaxis_title='Preço',
        xaxis_rangeslider_visible=False,
        height=800,
        showlegend=False
    )

    fig.update_yaxes(title_text="Volume", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    if st.checkbox("Mostrar dados brutos"):
        st.write(df)
else:
    st.warning("Não foi possível obter dados para o ativo selecionado na Testnet. Por favor, tente outro ativo ou verifique a disponibilidade de dados na Testnet.")