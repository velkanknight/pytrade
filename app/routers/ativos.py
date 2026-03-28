from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from typing import Optional
import MetaTrader5 as mt5
import pandas as pd

from app.mt5_client import get_mt5

router = APIRouter(prefix="/ativos", tags=["Ativos"])

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


@router.get("/listar", summary="Lista todos os ativos disponíveis no MT5")
def listar_ativos(mt5=Depends(get_mt5)):
    """Retorna todos os símbolos disponíveis na plataforma."""
    simbolos = mt5.symbols_get()
    if simbolos is None:
        raise HTTPException(status_code=503, detail="Erro ao listar ativos")
    return [s.name for s in simbolos]


@router.get("/{ativo}/info", summary="Informações detalhadas de um ativo")
def info_ativo(ativo: str, mt5=Depends(get_mt5)):
    """Retorna todas as propriedades do símbolo informado."""
    mt5.symbol_select(ativo, True)
    info = mt5.symbol_info(ativo)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Ativo '{ativo}' não encontrado")
    return info._asdict()


@router.get("/{ativo}/tick", summary="Cotação em tempo real (último tick)")
def tick_ativo(ativo: str, mt5=Depends(get_mt5)):
    """Retorna o último tick do ativo (bid, ask, last, volume)."""
    mt5.symbol_select(ativo, True)
    tick = mt5.symbol_info_tick(ativo)
    if tick is None:
        raise HTTPException(status_code=404, detail=f"Tick não disponível para '{ativo}'")
    return tick._asdict()


@router.get("/{ativo}/ohlc", summary="Dados OHLC históricos")
def ohlc_ativo(
    ativo: str,
    timeframe: str = Query("H1", description="Timeframe: M1, M5, M15, M30, H1, H4, D1, W1, MN1"),
    barras: int = Query(100, gt=0, le=10000, description="Quantidade de barras"),
    mt5=Depends(get_mt5),
):
    """Retorna candles OHLC históricos do ativo no timeframe especificado."""
    tf = TIMEFRAMES.get(timeframe.upper())
    if tf is None:
        raise HTTPException(status_code=400, detail=f"Timeframe inválido. Use: {list(TIMEFRAMES.keys())}")

    mt5.symbol_select(ativo, True)
    rates = mt5.copy_rates_from(ativo, tf, datetime.now(), barras)
    if rates is None or len(rates) == 0:
        raise HTTPException(status_code=404, detail=f"Sem dados para '{ativo}' no timeframe '{timeframe}'")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s").astype(str)
    return df.to_dict(orient="records")


@router.get("/{ativo}/ohlc/periodo", summary="Dados OHLC em período específico")
def ohlc_periodo(
    ativo: str,
    timeframe: str = Query("D1"),
    data_inicio: str = Query(..., description="Data início (YYYY-MM-DD)"),
    data_fim: str = Query(..., description="Data fim (YYYY-MM-DD)"),
    mt5=Depends(get_mt5),
):
    """Retorna candles OHLC entre duas datas."""
    tf = TIMEFRAMES.get(timeframe.upper())
    if tf is None:
        raise HTTPException(status_code=400, detail=f"Timeframe inválido. Use: {list(TIMEFRAMES.keys())}")

    try:
        dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        dt_fim = datetime.strptime(data_fim, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")

    mt5.symbol_select(ativo, True)
    rates = mt5.copy_rates_range(ativo, tf, dt_inicio, dt_fim)
    if rates is None or len(rates) == 0:
        raise HTTPException(status_code=404, detail="Sem dados para o período informado")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s").astype(str)
    return df.to_dict(orient="records")
