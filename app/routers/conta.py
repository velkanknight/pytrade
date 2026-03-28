from fastapi import APIRouter, Depends, HTTPException
import MetaTrader5 as mt5
import pandas as pd

from app.mt5_client import get_mt5

router = APIRouter(prefix="/conta", tags=["Conta"])


@router.get("/info", summary="Informações da conta MT5")
def info_conta(mt5=Depends(get_mt5)):
    """Retorna todas as informações da conta conectada ao MT5."""
    info = mt5.account_info()
    if info is None:
        raise HTTPException(status_code=503, detail=f"Erro ao obter conta: {mt5.last_error()}")
    return info._asdict()


@router.get("/saldo", summary="Saldo, equity e margem da conta")
def saldo_conta(mt5=Depends(get_mt5)):
    """Retorna saldo, equity, margem livre e margem utilizada."""
    info = mt5.account_info()
    if info is None:
        raise HTTPException(status_code=503, detail=f"Erro ao obter conta: {mt5.last_error()}")
    return {
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "margin_free": info.margin_free,
        "margin_level": info.margin_level,
        "currency": info.currency,
    }
