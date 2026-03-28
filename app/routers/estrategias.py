from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

from app.mt5_client import get_mt5
from app.schemas.models import BacktestRequest

router = APIRouter(prefix="/estrategias", tags=["Estratégias"])


def _calcular_cruzamento_media(mt5, ativo: str, sma_rapida: int, sma_lenta: int, barras: int) -> pd.DataFrame:
    """Calcula a estratégia de cruzamento de médias móveis."""
    mt5.symbol_select(ativo, True)
    rates = mt5.copy_rates_from(ativo, mt5.TIMEFRAME_D1, datetime.now(), barras)
    if rates is None or len(rates) == 0:
        raise HTTPException(status_code=404, detail=f"Sem dados históricos para '{ativo}'")

    data = pd.DataFrame(rates)
    data["time"] = pd.to_datetime(data["time"], unit="s")
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
