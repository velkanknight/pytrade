from fastapi import FastAPI
from app.routers import conta, ativos, ordens, estrategias

app = FastAPI(
    title="MT5 Trading API",
    description="API REST para automação de negociações no MetaTrader 5.",
    version="1.0.0",
)

app.include_router(conta.router)
app.include_router(ativos.router)
app.include_router(ordens.router)
app.include_router(estrategias.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "MT5 Trading API online"}
