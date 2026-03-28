from pydantic import BaseModel, Field
from typing import Optional
from enum import IntEnum


# ---------------------------------------------------------------------------
# Ordens
# ---------------------------------------------------------------------------

class TipoOrdem(str):
    COMPRA = "compra"
    VENDA = "venda"


class OrdemRequest(BaseModel):
    ativo: str = Field(..., example="EURUSD")
    quantidade: float = Field(1.0, gt=0, example=1.0)
    sl: int = Field(300, ge=0, description="Stop Loss em pontos")
    tp: int = Field(300, ge=0, description="Take Profit em pontos")


class FechamentoRequest(BaseModel):
    ativo: str = Field(..., example="EURUSD")
    ticket: int = Field(..., description="Ticket da posição aberta")
    quantidade: float = Field(..., gt=0)
    tipo_ordem: int = Field(..., description="0=BUY, 1=SELL")
    magic: int = Field(10132021)
    deviation: int = Field(0)


# ---------------------------------------------------------------------------
# Coleta de dados
# ---------------------------------------------------------------------------

class TimeframeEnum(str):
    M1  = "M1"
    M5  = "M5"
    M15 = "M15"
    M30 = "M30"
    H1  = "H1"
    H4  = "H4"
    D1  = "D1"
    W1  = "W1"
    MN1 = "MN1"


# ---------------------------------------------------------------------------
# Estratégias
# ---------------------------------------------------------------------------

class BacktestRequest(BaseModel):
    ativo: str = Field(..., example="EURUSD")
    sma_rapida: int = Field(43, gt=0, description="Período da média rápida")
    sma_lenta: int = Field(252, gt=0, description="Período da média lenta")
    barras: int = Field(2500, gt=0, description="Quantidade de barras históricas (D1)")
