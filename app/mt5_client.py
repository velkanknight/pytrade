import MetaTrader5 as mt5


def connect() -> bool:
    """Inicializa a conexão com o MetaTrader5."""
    if not mt5.initialize():
        raise RuntimeError(f"Falha ao conectar ao MT5: {mt5.last_error()}")
    return True


def disconnect():
    """Encerra a conexão com o MetaTrader5."""
    mt5.shutdown()


def get_mt5():
    """Dependency para FastAPI: garante conexão ativa a cada request."""
    connect()
    try:
        yield mt5
    finally:
        disconnect()
