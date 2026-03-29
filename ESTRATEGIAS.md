# Guia de Estratégias — MT5 Trading API

Este documento explica como usar cada estratégia disponível na API.
Use a URL base da sua API (ex: `https://sua-url.trycloudflare.com`).

---

## 1. Magic Sale (MACD Customizado)

### O que faz
Calcula a diferença entre duas médias móveis simples (SMA) e aplica uma média ponderada (WMA) como linha de sinal. Quando a diferença cruza a linha de sinal, gera sinais de compra ou venda.

### Lógica
- `buffer1 = SMA(close, ma_fast) - SMA(close, ma_slow)`
- `buffer2 = WMA(buffer1, signal_period)`
- **COMPRA** → `buffer1` cruza **acima** de `buffer2`
- **VENDA** → `buffer1` cruza **abaixo** de `buffer2`

### Sinal atual

```
POST /estrategias/magic-sale/sinal
Content-Type: application/json

{
  "ativo": "EURUSD",
  "timeframe": "M5",
  "ma_fast": 1,
  "ma_slow": 34,
  "signal_period": 4,
  "barras": 500
}
```

**Resposta:**
```json
{
  "ativo": "EURUSD",
  "timeframe": "M5",
  "sinal": "COMPRA",
  "close": 1.08234,
  "buffer1": 0.00012,
  "buffer2": 0.00008,
  "timestamp": "2026-03-29 10:30:00"
}
```

Sinais possíveis: `COMPRA`, `VENDA`, `TENDÊNCIA DE ALTA`, `TENDÊNCIA DE BAIXA`

### Histórico de sinais

```
POST /estrategias/magic-sale/historico
Content-Type: application/json

{
  "ativo": "EURUSD",
  "timeframe": "M5",
  "ma_fast": 1,
  "ma_slow": 34,
  "signal_period": 4,
  "barras": 500
}
```

Retorna uma lista com todos os sinais de COMPRA e VENDA no período.

---

## 2. Engolfo com Filtro de Tendência

### O que faz
Detecta padrões de candle **Engolfo** (engulfing) e **Outside Bar**, confirmados por 3 médias móveis como filtro de tendência.

### Lógica

**Engolfo de Alta (TOURO):**
- Candle atual é de alta (close > open)
- Candle anterior é de baixa (close < open)
- Corpo do candle atual engolfa o anterior
- Preço está **acima** das 3 médias (MA fast > MA slow > MA trend)

**Engolfo de Baixa (URSO):**
- Candle atual é de baixa (close < open)
- Candle anterior é de alta (close > open)
- Corpo do candle atual engolfa o anterior
- Preço está **abaixo** das 3 médias (MA fast < MA slow < MA trend)

**Outside Bar (SNIPER):**
- 3 candles consecutivos na mesma direção
- 1 candle de pullback (direção oposta)
- Candle atual confirma a direção original

### Sinal atual

```
POST /estrategias/engolfo/sinal
Content-Type: application/json

{
  "ativo": "EURUSD",
  "timeframe": "M5",
  "ma_fast": 3,
  "ma_slow": 7,
  "ma_trend": 100,
  "barras": 500
}
```

**Resposta:**
```json
{
  "ativo": "EURUSD",
  "timeframe": "M5",
  "sinal": "TOURO (ENGOLFO DE ALTA)",
  "close": 1.08234,
  "ma_fast": 1.08200,
  "ma_slow": 1.08150,
  "ma_trend": 1.08000,
  "timestamp": "2026-03-29 10:30:00"
}
```

Sinais possíveis:
- `TOURO (ENGOLFO DE ALTA)` — engolfo de alta confirmado pelas 3 MAs
- `URSO (ENGOLFO DE BAIXA)` — engolfo de baixa confirmado pelas 3 MAs
- `SNIPER TOURO (OUTSIDE BAR)` — outside bar de alta
- `SNIPER URSO (OUTSIDE BAR)` — outside bar de baixa
- `TENDÊNCIA DE ALTA` — sem padrão, mas preço acima das 3 MAs
- `TENDÊNCIA DE BAIXA` — sem padrão, mas preço abaixo das 3 MAs
- `NEUTRO` — sem padrão e sem tendência clara

### Histórico de sinais

```
POST /estrategias/engolfo/historico
Content-Type: application/json

{
  "ativo": "EURUSD",
  "timeframe": "M5",
  "ma_fast": 3,
  "ma_slow": 7,
  "ma_trend": 100,
  "barras": 500
}
```

---

## 3. Suporte e Resistência

### O que faz
Calcula níveis de suporte e resistência usando:
- **Pivôs:** pontos onde o preço fez topo (resistência) ou fundo (suporte) nos últimos 5 candles
- **Highest/Lowest:** maior topo e menor fundo em múltiplos períodos

### Sinal atual

```
POST /estrategias/suporte-resistencia
Content-Type: application/json

{
  "ativo": "EURUSD",
  "timeframe": "H1",
  "barras": 500,
  "periodos": [10, 30, 60, 100, 150, 200]
}
```

**Resposta:**
```json
{
  "ativo": "EURUSD",
  "timeframe": "H1",
  "ultimo_pivot_resistencia": 1.09500,
  "ultimo_pivot_suporte": 1.07800,
  "total_pivots_resistencia": 12,
  "total_pivots_suporte": 14,
  "niveis": {
    "HH_10": 1.08500,
    "LL_10": 1.08100,
    "HH_30": 1.09000,
    "LL_30": 1.07900,
    "HH_60": 1.09500,
    "LL_60": 1.07500,
    "HH_100": 1.09800,
    "LL_100": 1.07200,
    "HH_150": 1.10000,
    "LL_150": 1.06800,
    "HH_200": 1.10200,
    "LL_200": 1.06500
  },
  "close_atual": 1.08234,
  "timestamp": "2026-03-29 10:00:00"
}
```

### Como interpretar
- `HH_X` = maior topo das últimas X barras (resistência)
- `LL_X` = menor fundo das últimas X barras (suporte)
- Se o preço está perto de um `HH`, pode haver resistência (dificuldade de subir)
- Se o preço está perto de um `LL`, pode haver suporte (dificuldade de cair)

---

## 4. Cruzamento de Médias Móveis

### O que faz
Estratégia clássica de cruzamento de duas médias móveis simples (SMA).

### Lógica
- **COMPRA** → SMA rápida cruza **acima** da SMA lenta
- **VENDA** → SMA rápida cruza **abaixo** da SMA lenta

### Backtest

```
POST /estrategias/cruzamento-media/backtest
Content-Type: application/json

{
  "ativo": "EURUSD",
  "sma_rapida": 43,
  "sma_lenta": 252,
  "barras": 2500
}
```

Retorna: retorno acumulado, retorno da estratégia vs buy & hold, e drawdown máximo.

### Sinal atual

```
POST /estrategias/cruzamento-media/sinal
Content-Type: application/json

{
  "ativo": "EURUSD",
  "sma_rapida": 43,
  "sma_lenta": 252,
  "barras": 2500
}
```

---

## Parâmetros comuns

| Parâmetro | Descrição | Valores |
|-----------|-----------|---------|
| `ativo` | Símbolo do ativo no MT5 | `EURUSD`, `GBPUSD`, `BTCUSD`, etc |
| `timeframe` | Período do candle | `M1`, `M5`, `M15`, `M30`, `H1`, `H4`, `D1` |
| `barras` | Quantidade de candles históricos | 100 a 10000 |

---

## Fluxo recomendado

1. **Consulte suporte/resistência** para saber os níveis importantes
2. **Verifique o sinal do Engolfo** para confirmar padrão de candle + tendência
3. **Confirme com Magic Sale** para validar o momentum
4. **Execute a ordem** via `/ordens/compra` ou `/ordens/venda`

```
suporte-resistencia → engolfo/sinal → magic-sale/sinal → ordens/compra ou ordens/venda
```
