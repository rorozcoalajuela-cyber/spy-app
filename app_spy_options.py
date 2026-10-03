import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, time

st.set_page_config(page_title="SPY - Detector Opciones CALL/PUT", layout="wide")
st.title("🎯 Detector de Opciones CALL / PUT - SPY (1 Hora)")
st.caption("Análisis de las primeras 4 horas de mercado con SMAs 20, 40, 100 y 200")

# Cargar datos intradía de 1 hora (yfinance permite hasta 730 días en temporalidad 1h)
@st.cache_data(ttl=300)
def cargar_datos_spy():
    df = yf.download("SPY", period="60d", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # Convertir zona horaria a Nueva York (EST/EDT)
    df.index = pd.to_datetime(df.index).tz_convert("America/New_York")
    return df

try:
    df_raw = cargar_datos_spy()
    
    # Selección de fecha
    fechas_disponibles = sorted(list(set(df_raw.index.date)), reverse=True)
    fecha_sel = st.sidebar.selectbox("Seleccionar Fecha de Análisis", fechas_disponibles, index=0)

    # Filtrar datos de la sesión seleccionada
    df_dia = df_raw[df_raw.index.date == fecha_sel].copy()

    # Ventana de las primeras 4 horas (09:30 a 13:30 EST)
    hora_inicio = time(9, 30)
    hora_fin = time(13, 30)
    df_4h = df_dia[(df_dia.index.time >= hora_inicio) & (df_dia.index.time <= hora_fin)].copy()

    # Cálculo de Medias Móviles Simples (SMA) en temporalidad horaria
    # Se calculan sobre todo el dataset para no perder contexto histórico
    df_raw['SMA_20'] = df_raw['Close'].rolling(window=20).mean()
    df_raw['SMA_40'] = df_raw['Close'].rolling(window=40).mean()
    df_raw['SMA_100'] = df_raw['Close'].rolling(window=100).mean()
    df_raw['SMA_200'] = df_raw['Close'].rolling(window=200).mean()

    # Extraer los datos calculados para el día y la ventana de 4 horas
    df_4h = df_raw.loc[df_4h.index].copy()

    if df_4h.empty:
        st.warning("No hay suficientes datos horarias para la fecha seleccionada dentro del horario 09:30 - 13:30 EST.")
    else:
        # Valores de la última vela disponible en el bloque de 4h
        ultimo_precio = float(df_4h['Close'].iloc[-1])
        sma20 = float(df_4h['SMA_20'].iloc[-1])
        sma40 = float(df_4h['SMA_40'].iloc[-1])
        sma100 = float(df_4h['SMA_100'].iloc[-1])
        sma200 = float(df_4h['SMA_200'].iloc[-1])

        # EVALUACIÓN DE SEÑAL OPERATIVA (CALL / PUT)
        cond_call = ultimo_precio > sma20 and sma20 > sma40
        cond_put = ultimo_precio < sma20 and sma20 < sma40
        alineacion_fuerte_alcista = sma20 > sma40 > sma100 > sma200
        alineacion_fuerte_bajista = sma20 < sma40 < sma100 < sma200

        # PANEL DE SEÑAL PRINCIPAL
        st.subheader("📢 Recomendación Operativa")
        col_sig1, col_sig2 = st.columns([1, 2])

        with col_sig1:
            if cond_call:
                st.success("🟢 **SEÑAL SUGERIDA: CALL**")
                st.metric("Inclinación", "ALCISTA", f"+{(ultimo_precio - sma20):.2f} sobre SMA20")
            elif cond_put:
                st.error("🔴 **SEÑAL SUGERIDA: PUT**")
                st.metric("Inclinación", "BAJISTA", f"{(ultimo_precio - sma20):.2f} bajo SMA20")
            else:
                st.warning("🟡 **SEÑAL: EN RANGO / NEUTRAL**")
                st.metric("Inclinación", "CONSOLIDACIÓN", "Sin tendencia clara")

        with col_sig2:
            st.markdown("**Análisis de Estructura de Medias Móviles:**")
            st.write(f"- **Precio Actual:** ${ultimo_precio:.2f}")
            st.write(f"- **SMA 20:** ${sma20:.2f} | **SMA 40:** ${sma40:.2f}")
            st.write(f"- **SMA 100:** ${sma100:.2f} | **SMA 200:** ${sma200:.2f}")
            
            if alineacion_fuerte_alcista:
                st.info("⭐ **Estructura Ideal Alcista:** Alineación perfecta SMA 20 > 40 > 100 > 200.")
            elif alineacion_fuerte_bajista:
                st.info("⚠️ **Estructura Ideal Bajista:** Alineación perfecta SMA 20 < 40 < 100 < 200.")

        # PROYECCIÓN PARA EL DÍA SIGUIENTE
        st.subheader("🔮 Proyección de Comportamiento para la Apertura de Mañana")
        
        # Lógica de estimación de apertura
        cierre_4h = ultimo_precio
        variacion_cierre_sma20 = ((cierre_4h - sma20) / sma20) * 100

        if variacion_cierre_sma20 > 0.5:
            st.markdown("""
            * **Sesgo Esperado:** 🟢 **Apertura Alcista / Continuación de Impulso**
            * **Explicación:** El SPY mantiene fuerte presión compradora al cierre de las primeras 4 horas respecto a la SMA 20. Si no hay eventos macroeconómicos adversos, la inercia apunta a un *Gap Up* o continuidad de compras en la apertura de mañana.
            """)
        elif variacion_cierre_sma20 < -0.5:
            st.markdown("""
            * **Sesgo Esperado:** 🔴 **Apertura Bajista / Continuación de Presión Vendedora**
            * **Explicación:** El precio cerró la ventana de 4 horas con claro rechazo por debajo de la SMA 20, sugiriendo dominancia de vendedores para el inicio de la siguiente sesión.
            """)
        else:
            st.markdown("""
            * **Sesgo Esperado:** 🟡 **Apertura en Rango / Indecisión**
            * **Explicación:** El precio se encuentra comprimido cerca de la SMA 20. Se anticipa una apertura lateral a la espera de volumen que defina la dirección del movimiento.
            """)

        # GRÁFICO INTERACTIVO EN TEMPORALIDAD 1 HORA
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df_4h.index.strftime('%Y-%m-%d %H:%M'),
            open=df_4h['Open'], high=df_4h['High'],
            low=df_4h['Low'], close=df_4h['Close'],
            name="SPY (1h)"
        ))

        # Trazado de las 4 Medias Móviles
        fig.add_trace(go.Scatter(x=df_4h.index.strftime('%Y-%m-%d %H:%M'), y=df_4h['SMA_20'], name="SMA 20", line=dict(color="green", width=2)))
        fig.add_trace(go.Scatter(x=df_4h.index.strftime('%Y-%m-%d %H:%M'), y=df_4h['SMA_40'], name="SMA 40", line=dict(color="orange", width=2)))
        fig.add_trace(go.Scatter(x=df_4h.index.strftime('%Y-%m-%d %H:%M'), y=df_4h['SMA_100'], name="SMA 100", line=dict(color="blue", width=1.5)))
        fig.add_trace(go.Scatter(x=df_4h.index.strftime('%Y-%m-%d %H:%M'), y=df_4h['SMA_200'], name="SMA 200", line=dict(color="purple", width=1.5)))

        fig.update_layout(
            title=f"SPY 1h - Primeras 4 Horas (09:30 - 13:30 EST) | Fecha: {fecha_sel}",
            yaxis_title="Precio (USD)",
            xaxis_title="Hora de NY (EST)",
            xaxis_rangeslider_visible=False,
            template="plotly_white",
            height=550
        )

        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar o procesar los datos: {e}")