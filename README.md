# MT5 Trading API

API REST construída com **FastAPI** para expor as funcionalidades de negociação do **MetaTrader 5**, permitindo automação de estratégias via HTTP.

---

## Estrutura do Projeto

```
app/
├── main.py                   # Entrada da aplicação
├── mt5_client.py             # Gerenciamento de conexão com MT5
├── routers/
│   ├── conta.py              # Informações e saldo da conta
│   ├── ativos.py             # Consulta e coleta de dados de ativos
│   ├── ordens.py             # Envio, fechamento e histórico de ordens
│   └── estrategias.py        # Backtest e sinais de estratégias
└── schemas/
    └── models.py             # Modelos Pydantic (validação de entrada)
```

---

## Pré-requisitos

- Python 3.9+ instalado e adicionado ao PATH
- MetaTrader 5 instalado e **aberto** na máquina
- Conta demo ou real configurada no MT5

---

## Instalação e execução (passo a passo)

### 1. Clone o repositório
```powershell
git clone https://github.com/velkanknight/pytrade.git
cd pytrade
```

### 2. Crie o ambiente virtual
```powershell
python -m venv .venv
```

### 3. Ative o ambiente virtual
```powershell
.venv\Scripts\Activate.ps1
```

> ⚠️ Se receber erro de permissão no PowerShell, rode antes:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

### 4. Instale as dependências
```powershell
pip install -r requirements.txt
```

### 5. Suba a API
```powershell
uvicorn app.main:app --reload
```

A API estará disponível em: `http://127.0.0.1:8000`

Documentação interativa (Swagger): `http://127.0.0.1:8000/docs`

---

## Execuções seguintes

Após a primeira instalação, basta ativar o ambiente e subir:
```powershell
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

---

## Endpoints

### 🔑 Conta
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/conta/info` | Todas as informações da conta MT5 |
| GET | `/conta/saldo` | Saldo, equity, margem livre |

### 📊 Ativos
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/ativos/listar` | Lista todos os ativos disponíveis |
| GET | `/ativos/{ativo}/info` | Informações detalhadas do ativo |
| GET | `/ativos/{ativo}/tick` | Cotação em tempo real (bid/ask/last) |
| GET | `/ativos/{ativo}/ohlc` | Dados OHLC históricos (timeframe + barras) |
| GET | `/ativos/{ativo}/ohlc/periodo` | Dados OHLC por intervalo de datas |

### 📋 Ordens
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/ordens/compra` | Enviar ordem de compra a mercado |
| POST | `/ordens/venda` | Enviar ordem de venda a mercado |
| POST | `/ordens/fechar` | Fechar posição aberta pelo ticket |
| GET | `/ordens/abertas` | Listar ordens pendentes |
| GET | `/ordens/posicoes` | Listar posições abertas |
| GET | `/ordens/historico` | Histórico de negócios (últimos 30 dias) |

### 📈 Estratégias
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/estrategias/cruzamento-media/backtest` | Backtest de cruzamento de médias móveis |
| POST | `/estrategias/cruzamento-media/sinal` | Sinal atual da estratégia (COMPRA/VENDA) |

---

## Exemplos de Uso

### Obter cotação em tempo real
```
GET /ativos/EURUSD/tick
```

### Enviar ordem de compra
```json
POST /ordens/compra
{
  "ativo": "EURUSD",
  "quantidade": 1.0,
  "sl": 300,
  "tp": 300
}
```

### Backtest de cruzamento de médias
```json
POST /estrategias/cruzamento-media/backtest
{
  "ativo": "EURUSD",
  "sma_rapida": 43,
  "sma_lenta": 252,
  "barras": 2500
}
```

---

## Notas Importantes

- Certifique-se de que o MetaTrader 5 esteja em execução antes de iniciar a API
- Entenda completamente as estratégias antes de executá-las com dinheiro real
- Sempre monitore a execução de ordens automatizadas

## Aviso de Risco

O trading algorítmico envolve riscos significativos. Este código é fornecido apenas para fins educacionais. O autor não se responsabiliza por perdas financeiras decorrentes do uso deste software.

---

## Scripts originais (referência)

### Configuração e Conexão
- `00-initialize_mt5.py` - Inicialização básica da conexão com o MetaTrader 5
- `01-informacoes_conta_mt5.py` - Obtém informações da conta do usuário

### Coleta de Dados
- `02-ativos_mt5.py` a `08-dados_investpy.py` - Scripts para coleta de dados de ativos, informações de mercado, preços OHLC e dados em tempo real

### Backtesting e Estratégias
- `09-backtest_cruzamento_media_mt5.py` - Backtest da estratégia de cruzamento de médias
- `10-rebaixamento_estrategia_cruzamento_media_mt5.py` - Análise de rebaixamento para estratégia de cruzamento
- `11-estrategia_compra_queda_yfinance.py` - Estratégia de compra na queda com dados do Yahoo Finance

### Execução de Ordens
- `12-envio_ordem_mt5.py` - Script para envio de ordens de compra e venda
- `13-ordem_fechamento_mt5.py` - Script para fechamento de ordens

### Análise Preditiva
- `14-previ_prophet.py` - Previsão usando Facebook Prophet
- `15-regressao_linear.py` - Implementação de modelos de regressão linear
- `16-rede_neural.py` - Implementação de redes neurais para previsão

### Notebooks
- `notebook-01.ipynb` a `notebook-04.ipynb` - Jupyter notebooks com análises e exemplos práticos

## Requisitos
- Python 3.7+
- MetaTrader 5 instalado e configurado
- Conta em uma corretora compatível com MetaTrader 5
- Bibliotecas Python listadas em requirements.txt

## Instalação

### Usando pip
```bash
# Clone o repositório
git clone https://github.com/caiquemiranda/python-algo-trading.git
cd python-algo-trading

# Instale as dependências
pip install -r requirements.txt
```

### Usando Docker
```bash
# Clone o repositório
git clone https://github.com/caiquemiranda/python-algo-trading.git
cd python-algo-trading

# Construa a imagem Docker
docker build -t python-algo-trading .

# Execute o container
docker run -it python-algo-trading
```

## Configuração

1. Instale o MetaTrader 5 em seu computador
2. Configure sua conta em uma corretora compatível
3. Faça login na plataforma MetaTrader 5
4. Execute os scripts conforme sua necessidade

## Uso

### Exemplos Básicos

1. Inicializar conexão com MetaTrader 5:
```bash
python 00-initialize_mt5.py
```

2. Verificar informações da conta:
```bash
python 01-informacoes_conta_mt5.py
```

3. Executar uma estratégia de trading:
```bash
python 12-envio_ordem_mt5.py
```

### Executando Backtests

```bash
python 09-backtest_cruzamento_media_mt5.py
```

### Usando Modelos Preditivos

```bash
python 15-regressao_linear.py
```

## Notas Importantes

- Certifique-se de que o MetaTrader 5 esteja em execução antes de rodar os scripts
- Entenda completamente as estratégias antes de executá-las com dinheiro real
- Comece com pequenas quantidades para testar o funcionamento do sistema
- Sempre monitore a execução dos scripts de trading automatizado

## Aviso de Risco

O trading algorítmico envolve riscos significativos. Este código é fornecido apenas para fins educacionais e de pesquisa. Não recomendamos o uso destes scripts para trading real sem uma compreensão completa do mercado e dos riscos envolvidos. O autor não se responsabiliza por quaisquer perdas financeiras decorrentes do uso deste software.

## Licença
Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes.
