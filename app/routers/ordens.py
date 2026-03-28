from fastapi import APIRouter, Depends, HTTPException
import MetaTrader5 as mt5
import pandas as pd

from app.mt5_client import get_mt5
from app.schemas.models import OrdemRequest, FechamentoRequest

router = APIRouter(prefix="/ordens", tags=["Ordens"])


def _enviar_ordem(mt5, request: dict):
    resultado = mt5.order_send(request)
    if resultado is None or resultado.retcode != mt5.TRADE_RETCODE_DONE:
        raise HTTPException(
            status_code=400,
            detail=f"Falha ao enviar ordem. Retcode: {resultado.retcode if resultado else 'None'} - {mt5.last_error()}",
        )
    return resultado._asdict()


@router.post("/compra", summary="Enviar ordem de compra a mercado")
def enviar_compra(body: OrdemRequest, mt5=Depends(get_mt5)):
    """Envia uma ordem de compra (BUY) a mercado com SL e TP em pontos."""
    mt5.symbol_select(body.ativo, True)
    price = mt5.symbol_info_tick(body.ativo).ask
    point = mt5.symbol_info(body.ativo).point

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": body.ativo,
        "volume": float(body.quantidade),
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "sl": price - body.sl * point,
        "tp": price + body.tp * point,
        "deviation": 0,
        "magic": 10132021,
        "comment": "API - Ordem de Compra",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    return _enviar_ordem(mt5, request)


@router.post("/venda", summary="Enviar ordem de venda a mercado")
def enviar_venda(body: OrdemRequest, mt5=Depends(get_mt5)):
    """Envia uma ordem de venda (SELL) a mercado com SL e TP em pontos."""
    mt5.symbol_select(body.ativo, True)
    price = mt5.symbol_info_tick(body.ativo).bid
    point = mt5.symbol_info(body.ativo).point

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": body.ativo,
        "volume": float(body.quantidade),
        "type": mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": price + body.sl * point,
        "tp": price - body.tp * point,
        "deviation": 0,
        "magic": 10132021,
        "comment": "API - Ordem de Venda",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    return _enviar_ordem(mt5, request)


@router.post("/fechar", summary="Fechar uma posição aberta pelo ticket")
def fechar_ordem(body: FechamentoRequest, mt5=Depends(get_mt5)):
    """Fecha uma posição aberta usando o ticket informado."""
    mt5.symbol_select(body.ativo, True)

    if body.tipo_ordem == 0:  # posição de compra → fechar com venda
        price = mt5.symbol_info_tick(body.ativo).bid
        tipo = mt5.ORDER_TYPE_SELL
    else:  # posição de venda → fechar com compra
        price = mt5.symbol_info_tick(body.ativo).ask
        tipo = mt5.ORDER_TYPE_BUY

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": body.ticket,
        "symbol": body.ativo,
        "volume": float(body.quantidade),
        "deviation": body.deviation,
        "magic": body.magic,
        "type": tipo,
        "price": price,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    return _enviar_ordem(mt5, request)


@router.get("/abertas", summary="Listar todas as ordens pendentes abertas")
def listar_ordens(mt5=Depends(get_mt5)):
    """Retorna todas as ordens pendentes abertas."""
    ordens = mt5.orders_get()
    if ordens is None:
        return []
    df = pd.DataFrame(list(ordens), columns=ordens[0]._asdict().keys())
    df["time_setup"] = pd.to_datetime(df["time_setup"], unit="s").astype(str)
    return df.to_dict(orient="records")


@router.get("/posicoes", summary="Listar todas as posições abertas")
def listar_posicoes(ativo: str = None, mt5=Depends(get_mt5)):
    """Retorna posições abertas. Filtra por ativo se informado."""
    posicoes = mt5.positions_get(symbol=ativo) if ativo else mt5.positions_get()
    if posicoes is None or len(posicoes) == 0:
        return []
    df = pd.DataFrame(list(posicoes), columns=posicoes[0]._asdict().keys())
    df["time"] = pd.to_datetime(df["time"], unit="s").astype(str)
    return df.to_dict(orient="records")


@router.get("/historico", summary="Histórico de ordens executadas")
def historico_ordens(mt5=Depends(get_mt5)):
    """Retorna o histórico de negócios da sessão atual."""
    from datetime import datetime, timedelta
    inicio = datetime.now() - timedelta(days=30)
    deals = mt5.history_deals_get(inicio, datetime.now())
    if deals is None or len(deals) == 0:
        return []
    df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
    df["time"] = pd.to_datetime(df["time"], unit="s").astype(str)
    return df.to_dict(orient="records")
