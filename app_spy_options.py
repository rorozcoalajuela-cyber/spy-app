import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, time

st.set_page_config(page_title="SPY - Detector Opciones CALL/PUT", layout="wide")
st.title("🎯 Detector de Opciones CALL / PUT - SPY (1 Hora)")
st.caption("Análisis de la sesión completa de mercado (09:30 - 16:00 EST / 8 Horas) con SMAs 20, 40, 100 y 200")

# Cargar datos intradía de 1 hora
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
    
    # Cálculo de Medias Móviles Simples (SMA) sobre el dataset histórico completo
    df_raw['SMA_20'] = df_raw['Close'].rolling(window=20).mean()
    df_raw['SMA_40'] = df_raw['Close'].rolling(window=40).mean()
    df_raw['SMA_100'] = df_raw['Close'].rolling(window=100).mean()
    df_raw['SMA_200'] = df_raw['Close'].rolling(window=200).mean()

    # Selección de fecha
    fechas_disponibles = sorted(list(set(df_raw.index.date)), reverse=True)
    fecha_sel = st.sidebar.selectbox("Seleccionar Fecha de Análisis", fechas_disponibles, index=0)

    # Filtrar datos del día seleccionado
    df_dia = df_raw[df_raw.index.date == fecha_sel].copy()

    # Ventana de las 8 horas completas de mercado (09:30 a 16:00 EST / 07:30 a 14:00 CR)
    hora_inicio = time(9, 30)
    hora_fin = time(16, 0)
    df_8h = df_dia[(df_dia.index.time >= hora_inicio) & (df_dia.index.time <= hora_fin)].copy()

    if df_8h.empty:
        st.warning("No hay suficientes datos para la fecha seleccionada dentro del horario de mercado.")
    else:
        # Valores de la última vela disponible en la jornada (al cierre o la vela más reciente)
        ultimo_precio = float(df_8h['Close'].iloc[-1])
        sma20 = float(df_8h['SMA_20'].iloc[-1])
        sma40 = float(df_8h['SMA_40'].iloc[-1])
        sma100 = float(df_8h['SMA_100'].iloc[-1])
        sma200 = float(df_8h['SMA_200'].iloc[-1])

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
            st.markdown("**Estructura de Medias Móviles (1H):**")
            st.write(f"- **Último Precio:** ${ultimo_precio:.2f}")
            st.write(f"- **SMA 20:** ${sma20:.2f} | **SMA 40:** ${sma40:.2f}")
            st.write(f"- **SMA 100:** ${sma100:.2f} | **SMA 200:** ${sma200:.2f}")
            
            if alineacion_fuerte_alcista:
                st.info("⭐ **Estructura Ideal Alcista:** Alineación perfecta SMA 20 > 40 > 100 > 200.")
            elif alineacion_fuerte_bajista:
                st.info("⚠️ **Estructura Ideal Bajista:** Alineación perfecta SMA 20 < 40 < 100 < 200.")

        # PROYECCIÓN PARA LA APERTURA DEL DÍA SIGUIENTE (BASADO EN EL CIERRE DE SESIÓN)
        st.subheader("🔮 Proyección para la Apertura del Día Siguiente")
        
        cierre_sesion = ultimo_precio
        variacion_cierre_sma20 = ((cierre_sesion - sma20) / sma20) * 100

        if variacion_cierre_sma20 > 0.4:
            st.markdown("""
            * **Sesgo Esperado:** 🟢 **Apertura Alcista / Continuación de Impulso**
            * **Explicación:** El SPY cerró la sesión de 8 horas con fuerte presión compradora por encima de la SMA 20. Al mantener la estructura alcista en el cierre formal del mercado, se anticipa inercia de compras para la apertura de la siguiente jornada.
            """)
        elif variacion_cierre_sma20 < -0.4:
            st.markdown("""
            * **Sesgo Esperado:** 🔴 **Apertura Bajista / Continuación de Presión Vendedora**
            * **Explicación:** El SPY cerró la jornada completa con claro rechazo por debajo de la SMA 20. El cierre vendedora institucional sugiere ventaja a la baja para la apertura de mañana.
            """)
        else:
            st.markdown("""
            * **Sesgo Esperado:** 🟡 **Apertura en Rango / Indecisión**
            * **Explicación:** El precio cerró la sesión comprimido o muy cercano a la SMA 20. Se anticipa una apertura neutral/lateral a la espera de volumen en la sesión de la mañana.
            """)

        # GRÁFICO INTERACTIVO (SESIÓN COMPLETA 8 HORAS)
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df_8h.index.strftime('%Y-%m-%d %H:%M'),
            open=df_8h['Open'], high=df_8h['High'],
            low=df_8h['Low'], close=df_8h['Close'],
            name="SPY (1h)"
        ))

        # Medias Móviles
        fig.add_trace(go.Scatter(x=df_8h.index.strftime('%Y-%m-%d %H:%M'), y=df_8h['SMA_20'], name="SMA 20", line=dict(color="green", width=2)))
        fig.add_trace(go.Scatter(x=df_8h.index.strftime('%Y-%m-%d %H:%M'), y=df_8h['SMA_40'], name="SMA 40", line=dict(color="orange", width=2)))
        fig.add_trace(go.Scatter(x=df_8h.index.strftime('%Y-%m-%d %H:%M'), y=df_8h['SMA_100'], name="SMA 100", line=dict(color="blue", width=1.5)))
        fig.add_trace(go.Scatter(x=df_8h.index.strftime('%Y-%m-%d %H:%M'), y=df_8h['SMA_200'], name="SMA 200", line=dict(color="purple", width=1.5)))

        fig.update_layout(
            title=f"SPY 1h - Sesión Completa de Mercado (09:30 - 16:00 EST) | Fecha: {fecha_sel}",
            yaxis_title="Precio (USD)",
            xaxis_title="Hora de NY (EST)",
            xaxis_rangeslider_visible=False,
            template="plotly_white",
            height=550
        )

        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar o procesar los datos: {e}")
