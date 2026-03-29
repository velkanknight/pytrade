from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import List
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

from app.mt5_client import get_mt5
from app.schemas.models import (
    BacktestRequest,
    MagicSaleRequest,
    EngulfingRequest,
    SuporteResistenciaRequest,
)

router = APIRouter(prefix="/estrategias", tags=["Estratégias"])

TIMEFRAMES = {
    "M1":  mt5.TIMEFRAME_M1,
    "M5":  mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1":  mt5.TIMEFRAME_H1,
    "H4":  mt5.TIMEFRAME_H4,
    "D1":  mt5.TIMEFRAME_D1,
    "W1":  mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}


def _get_ohlc(mt5, ativo: str, timeframe: str, barras: int) -> pd.DataFrame:
    """Busca dados OHLC do MT5 e retorna DataFrame."""
    tf = TIMEFRAMES.get(timeframe.upper())
    if tf is None:
        raise HTTPException(status_code=400, detail=f"Timeframe inválido. Use: {list(TIMEFRAMES.keys())}")
    mt5.symbol_select(ativo, True)
    rates = mt5.copy_rates_from(ativo, tf, datetime.now(), barras)
    if rates is None or len(rates) == 0:
        raise HTTPException(status_code=404, detail=f"Sem dados históricos para '{ativo}'")
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df


def _wma(series: pd.Series, period: int) -> pd.Series:
    """Weighted Moving Average."""
    weights = np.arange(1, period + 1, dtype=float)
    return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


def _calcular_cruzamento_media(mt5, ativo: str, sma_rapida: int, sma_lenta: int, barras: int) -> pd.DataFrame:
    """Calcula a estratégia de cruzamento de médias móveis."""
    data = _get_ohlc(mt5, ativo, "D1", barras)
    data[f"sma_{sma_rapida}"] = data["close"].rolling(sma_rapida).mean()
    data[f"sma_{sma_lenta}"] = data["close"].rolling(sma_lenta).mean()
    data.dropna(inplace=True)
    data = data[["time", "close", f"sma_{sma_rapida}", f"sma_{sma_lenta}"]].set_index("time")
    return data


@router.post("/cruzamento-media/backtest", summary="Backtest da estratégia de cruzamento de médias")
def backtest_cruzamento_media(body: BacktestRequest, mt5=Depends(get_mt5)):
    """
    Executa backtest da estratégia de cruzamento de médias móveis simples (SMA).
    - Posição = 1 (comprado) quando SMA rápida > SMA lenta
    - Posição = -1 (vendido) quando SMA rápida < SMA lenta
    """
    data = _calcular_cruzamento_media(mt5, body.ativo, body.sma_rapida, body.sma_lenta, body.barras)

    sma_r = f"sma_{body.sma_rapida}"
    sma_l = f"sma_{body.sma_lenta}"

    data["posicao"] = np.where(data[sma_r] > data[sma_l], 1, -1)
    data["posicao"] = data["posicao"].shift(1)
    data.dropna(inplace=True)

    data["retornos"] = np.log(data["close"] / data["close"].shift(1))
    data.dropna(inplace=True)
    data["estrategia"] = data["posicao"] * data["retornos"]

    retorno_simples = data[["retornos", "estrategia"]].sum().to_dict()
    retorno_acumulado = (data[["retornos", "estrategia"]].sum().apply(np.exp) - 1).to_dict()

    # Drawdown máximo
    data["equity_curve"] = data["estrategia"].cumsum().apply(np.exp)
    data["drawdown"] = data["equity_curve"] / data["equity_curve"].cummax() - 1
    max_drawdown = float(data["drawdown"].min())

    return {
        "ativo": body.ativo,
        "sma_rapida": body.sma_rapida,
        "sma_lenta": body.sma_lenta,
        "barras_utilizadas": len(data),
        "retorno_simples": retorno_simples,
        "retorno_acumulado_percentual": {k: round(v * 100, 2) for k, v in retorno_acumulado.items()},
        "max_drawdown_percentual": round(max_drawdown * 100, 2),
    }


@router.post("/cruzamento-media/sinal", summary="Sinal atual da estratégia de cruzamento de médias")
def sinal_cruzamento_media(body: BacktestRequest, mt5=Depends(get_mt5)):
    """
    Retorna o sinal atual (COMPRA / VENDA / NEUTRO) baseado no cruzamento de médias.
    """
    data = _calcular_cruzamento_media(mt5, body.ativo, body.sma_rapida, body.sma_lenta, body.barras)

    sma_r = f"sma_{body.sma_rapida}"
    sma_l = f"sma_{body.sma_lenta}"

    ultima = data.iloc[-1]
    anterior = data.iloc[-2]

    cruzou_alta = anterior[sma_r] <= anterior[sma_l] and ultima[sma_r] > ultima[sma_l]
    cruzou_baixa = anterior[sma_r] >= anterior[sma_l] and ultima[sma_r] < ultima[sma_l]

    if cruzou_alta:
        sinal = "COMPRA"
    elif cruzou_baixa:
        sinal = "VENDA"
    elif ultima[sma_r] > ultima[sma_l]:
        sinal = "TENDÊNCIA DE ALTA"
    else:
        sinal = "TENDÊNCIA DE BAIXA"

    return {
        "ativo": body.ativo,
        "sinal": sinal,
        "close": float(ultima["close"]),
        f"sma_{body.sma_rapida}": float(ultima[sma_r]),
        f"sma_{body.sma_lenta}": float(ultima[sma_l]),
        "timestamp": str(data.index[-1]),
    }


# ===========================================================================
# MAGIC SALE — MACD customizado (SMA diff + WMA sinal)
# ===========================================================================

@router.post("/magic-sale/sinal", summary="Sinal da estratégia Magic Sale (MACD customizado)")
def sinal_magic_sale(body: MagicSaleRequest, mt5=Depends(get_mt5)):
    """
    Estratégia Magic Sale (LORRANY): MACD customizado.
    - buffer1 = SMA_rápida - SMA_lenta
    - buffer2 = WMA(buffer1, signal_period)
    - COMPRA quando buffer1 cruza acima de buffer2
    - VENDA quando buffer1 cruza abaixo de buffer2
    """
    data = _get_ohlc(mt5, body.ativo, body.timeframe, body.barras)

    data["sma_fast"] = data["close"].rolling(body.ma_fast).mean()
    data["sma_slow"] = data["close"].rolling(body.ma_slow).mean()
    data["buffer1"] = data["sma_fast"] - data["sma_slow"]
    data["buffer2"] = _wma(data["buffer1"], body.signal_period)
    data.dropna(inplace=True)

    if len(data) < 2:
        raise HTTPException(status_code=400, detail="Dados insuficientes para calcular sinal")

    # Detectar cruzamentos
    data["buy"] = (data["buffer1"] > data["buffer2"]) & (data["buffer1"].shift(1) <= data["buffer2"].shift(1))
    data["sell"] = (data["buffer1"] < data["buffer2"]) & (data["buffer1"].shift(1) >= data["buffer2"].shift(1))

    ultima = data.iloc[-1]

    if ultima["buy"]:
        sinal = "COMPRA"
    elif ultima["sell"]:
        sinal = "VENDA"
    elif ultima["buffer1"] > ultima["buffer2"]:
        sinal = "TENDÊNCIA DE ALTA"
    else:
        sinal = "TENDÊNCIA DE BAIXA"

    return {
        "ativo": body.ativo,
        "timeframe": body.timeframe,
        "sinal": sinal,
        "close": float(ultima["close"]),
        "buffer1": float(ultima["buffer1"]),
        "buffer2": float(ultima["buffer2"]),
        "timestamp": str(ultima["time"]),
    }


@router.post("/magic-sale/historico", summary="Histórico de sinais Magic Sale")
def historico_magic_sale(body: MagicSaleRequest, mt5=Depends(get_mt5)):
    """
    Retorna o histórico completo de sinais de COMPRA e VENDA da estratégia Magic Sale.
    """
    data = _get_ohlc(mt5, body.ativo, body.timeframe, body.barras)

    data["sma_fast"] = data["close"].rolling(body.ma_fast).mean()
    data["sma_slow"] = data["close"].rolling(body.ma_slow).mean()
    data["buffer1"] = data["sma_fast"] - data["sma_slow"]
    data["buffer2"] = _wma(data["buffer1"], body.signal_period)
    data.dropna(inplace=True)

    data["buy"] = (data["buffer1"] > data["buffer2"]) & (data["buffer1"].shift(1) <= data["buffer2"].shift(1))
    data["sell"] = (data["buffer1"] < data["buffer2"]) & (data["buffer1"].shift(1) >= data["buffer2"].shift(1))

    sinais = []
    for _, row in data.iterrows():
        if row["buy"]:
            sinais.append({"time": str(row["time"]), "sinal": "COMPRA", "close": float(row["close"])})
        elif row["sell"]:
            sinais.append({"time": str(row["time"]), "sinal": "VENDA", "close": float(row["close"])})

    return {
        "ativo": body.ativo,
        "timeframe": body.timeframe,
        "total_sinais": len(sinais),
        "sinais": sinais,
    }


# ===========================================================================
# ENGOLFO COM FILTRO DE TENDÊNCIA (SMA-ENG)
# ===========================================================================

def _detectar_engolfo(data: pd.DataFrame, ma_fast_col: str, ma_slow_col: str, ma_trend_col: str) -> pd.DataFrame:
    """Detecta padrões de engolfo com filtro de 3 médias móveis."""
    o = data["open"]
    c = data["close"]
    o1 = data["open"].shift(1)
    c1 = data["close"].shift(1)
    corpo = (c - o).abs()
    corpo1 = (c1 - o1).abs()
    ma_f = data[ma_fast_col]
    ma_s = data[ma_slow_col]
    ma_t = data[ma_trend_col]

    # Engolfo de Alta (TOURO)
    data["engolfo_alta"] = (
        (c > o) &             # candle atual de alta
        (c1 < o1) &           # candle anterior de baixa
        (c > o1) &            # close atual > open anterior
        (o <= c1) &           # open atual <= close anterior
        (corpo > corpo1) &    # corpo atual > corpo anterior
        (c > ma_f) &          # acima da MA rápida
        (ma_f > ma_s) &       # MA rápida > MA lenta
        (ma_s > ma_t)         # MA lenta > MA tendência
    )

    # Engolfo de Baixa (URSO)
    data["engolfo_baixa"] = (
        (c < o) &             # candle atual de baixa
        (c1 > o1) &           # candle anterior de alta
        (c < o1) &            # close atual < open anterior
        (o >= c1) &           # open atual >= close anterior
        (corpo > corpo1) &    # corpo atual > corpo anterior
        (c < ma_f) &          # abaixo da MA rápida
        (ma_f < ma_s) &       # MA rápida < MA lenta
        (ma_s < ma_t)         # MA lenta < MA tendência
    )

    return data


def _detectar_outside_bar(data: pd.DataFrame) -> pd.DataFrame:
    """Detecta padrão Outside Bar (SNIPER) - 3 candles consecutivos + reversão."""
    o = data["open"]
    c = data["close"]
    o1 = data["open"].shift(1)
    c1 = data["close"].shift(1)
    o2 = data["open"].shift(2)
    c2 = data["close"].shift(2)
    o3 = data["open"].shift(3)
    c3 = data["close"].shift(3)

    # Outside Bar COMPRA: 3 candles de alta + 1 de baixa (pullback) + candle alta
    data["outside_alta"] = (
        (o3 < c3) &           # candle -3 de alta
        (o2 < c2) &           # candle -2 de alta
        (o1 > c1) &           # candle -1 de baixa (pullback)
        (c1 > o2) &           # pullback não quebra a sequência
        (o1 > o2) &           # open do pullback acima
        (o < c)               # candle atual de alta (confirmação)
    )

    # Outside Bar VENDA: 3 candles de baixa + 1 de alta (pullback) + candle baixa
    data["outside_baixa"] = (
        (o3 > c3) &           # candle -3 de baixa
        (o2 > c2) &           # candle -2 de baixa
        (o1 < c1) &           # candle -1 de alta (pullback)
        (c1 < o2) &           # pullback não quebra a sequência
        (o1 < o2) &           # open do pullback abaixo
        (o > c)               # candle atual de baixa (confirmação)
    )

    return data


@router.post("/engolfo/sinal", summary="Sinal da estratégia de Engolfo com filtro de tendência")
def sinal_engolfo(body: EngulfingRequest, mt5=Depends(get_mt5)):
    """
    Estratégia SMA-ENG: detecta padrão de candle Engolfo confirmado por 3 médias móveis.
    - TOURO: engolfo de alta + preço acima das 3 MAs
    - URSO: engolfo de baixa + preço abaixo das 3 MAs
    - SNIPER TOURO/URSO: padrão Outside Bar (3 candles + reversão)
    """
    data = _get_ohlc(mt5, body.ativo, body.timeframe, body.barras)

    data["ma_fast"] = data["close"].rolling(body.ma_fast).mean()
    data["ma_slow"] = data["close"].rolling(body.ma_slow).mean()
    data["ma_trend"] = data["close"].rolling(body.ma_trend).mean()
    data.dropna(inplace=True)

    data = _detectar_engolfo(data, "ma_fast", "ma_slow", "ma_trend")
    data = _detectar_outside_bar(data)

    if len(data) < 1:
        raise HTTPException(status_code=400, detail="Dados insuficientes")

    ultima = data.iloc[-1]

    if ultima["engolfo_alta"]:
        sinal = "TOURO (ENGOLFO DE ALTA)"
    elif ultima["engolfo_baixa"]:
        sinal = "URSO (ENGOLFO DE BAIXA)"
    elif ultima["outside_alta"]:
        sinal = "SNIPER TOURO (OUTSIDE BAR)"
    elif ultima["outside_baixa"]:
        sinal = "SNIPER URSO (OUTSIDE BAR)"
    elif ultima["close"] > ultima["ma_fast"] > ultima["ma_slow"] > ultima["ma_trend"]:
        sinal = "TENDÊNCIA DE ALTA"
    elif ultima["close"] < ultima["ma_fast"] < ultima["ma_slow"] < ultima["ma_trend"]:
        sinal = "TENDÊNCIA DE BAIXA"
    else:
        sinal = "NEUTRO"

    return {
        "ativo": body.ativo,
        "timeframe": body.timeframe,
        "sinal": sinal,
        "close": float(ultima["close"]),
        "ma_fast": float(ultima["ma_fast"]),
        "ma_slow": float(ultima["ma_slow"]),
        "ma_trend": float(ultima["ma_trend"]),
        "timestamp": str(ultima["time"]),
    }


@router.post("/engolfo/historico", summary="Histórico de sinais de Engolfo")
def historico_engolfo(body: EngulfingRequest, mt5=Depends(get_mt5)):
    """
    Retorna o histórico completo de sinais de Engolfo e Outside Bar.
    """
    data = _get_ohlc(mt5, body.ativo, body.timeframe, body.barras)

    data["ma_fast"] = data["close"].rolling(body.ma_fast).mean()
    data["ma_slow"] = data["close"].rolling(body.ma_slow).mean()
    data["ma_trend"] = data["close"].rolling(body.ma_trend).mean()
    data.dropna(inplace=True)

    data = _detectar_engolfo(data, "ma_fast", "ma_slow", "ma_trend")
    data = _detectar_outside_bar(data)

    sinais = []
    for _, row in data.iterrows():
        if row["engolfo_alta"]:
            sinais.append({"time": str(row["time"]), "sinal": "TOURO (ENGOLFO)", "close": float(row["close"])})
        elif row["engolfo_baixa"]:
            sinais.append({"time": str(row["time"]), "sinal": "URSO (ENGOLFO)", "close": float(row["close"])})
        elif row["outside_alta"]:
            sinais.append({"time": str(row["time"]), "sinal": "SNIPER TOURO", "close": float(row["close"])})
        elif row["outside_baixa"]:
            sinais.append({"time": str(row["time"]), "sinal": "SNIPER URSO", "close": float(row["close"])})

    return {
        "ativo": body.ativo,
        "timeframe": body.timeframe,
        "total_sinais": len(sinais),
        "sinais": sinais,
    }


# ===========================================================================
# SUPORTE E RESISTÊNCIA (AXX SUPORT/RES)
# ===========================================================================

@router.post("/suporte-resistencia", summary="Níveis de suporte e resistência")
def suporte_resistencia(body: SuporteResistenciaRequest, mt5=Depends(get_mt5)):
    """
    Calcula níveis de suporte e resistência baseado em:
    - Pivôs de alta/baixa (5 candles)
    - Highest/Lowest em múltiplos períodos (10, 30, 60, 100, 150, 200)
    """
    data = _get_ohlc(mt5, body.ativo, body.timeframe, body.barras)

    if len(data) < 5:
        raise HTTPException(status_code=400, detail="Dados insuficientes")

    # Pivôs de alta (resistência): high[2] é maior que os 4 vizinhos
    data["pivot_high"] = np.nan
    for i in range(2, len(data) - 2):
        h = data["high"].iloc[i]
        if (h >= data["high"].iloc[i - 1] and
            h >= data["high"].iloc[i - 2] and
            h >= data["high"].iloc[i + 1] and
            h >= data["high"].iloc[i + 2]):
            data.iloc[i, data.columns.get_loc("pivot_high")] = h

    # Pivôs de baixa (suporte): low[2] é menor que os 4 vizinhos
    data["pivot_low"] = np.nan
    for i in range(2, len(data) - 2):
        lo = data["low"].iloc[i]
        if (lo <= data["low"].iloc[i - 1] and
            lo <= data["low"].iloc[i - 2] and
            lo <= data["low"].iloc[i + 1] and
            lo <= data["low"].iloc[i + 2]):
            data.iloc[i, data.columns.get_loc("pivot_low")] = lo

    # Último pivô válido
    last_resistance = data["pivot_high"].dropna()
    last_support = data["pivot_low"].dropna()

    # Highest/Lowest por período
    niveis = {}
    for p in body.periodos:
        if len(data) >= p:
            hh = float(data["high"].iloc[-p:].max())
            ll = float(data["low"].iloc[-p:].min())
            niveis[f"HH_{p}"] = hh
            niveis[f"LL_{p}"] = ll

    return {
        "ativo": body.ativo,
        "timeframe": body.timeframe,
        "ultimo_pivot_resistencia": float(last_resistance.iloc[-1]) if len(last_resistance) > 0 else None,
        "ultimo_pivot_suporte": float(last_support.iloc[-1]) if len(last_support) > 0 else None,
        "total_pivots_resistencia": len(last_resistance),
        "total_pivots_suporte": len(last_support),
        "niveis": niveis,
        "close_atual": float(data["close"].iloc[-1]),
        "timestamp": str(data["time"].iloc[-1]),
    }
