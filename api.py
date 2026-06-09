"""
API REST para consumo externo dos dados RFV.
Execute com: uvicorn api:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import numpy as np
from datetime import datetime, date

app = FastAPI(
    title="API RFV - Análise de Clientes",
    description="Endpoints para consumo programático dos dados de segmentação RFV",
    version="1.0.0"
)

# Permitir requisições de qualquer origem (ex: Streamlit, outros sistemas)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Geração dos dados e cálculo RFV (mesma lógica do Streamlit)
# ---------------------------------------------------------------------------

def gerar_dados_exemplo():
    np.random.seed(42)
    n_clientes = 1000
    datas = pd.date_range(start='2023-01-01', end='2024-12-31', freq='D')
    dados = {
        'cliente_id': np.random.choice(range(1, 201), n_clientes),
        'data_compra': np.random.choice(datas, n_clientes),
        'valor_compra': np.random.uniform(50, 1000, n_clientes).round(2)
    }
    df = pd.DataFrame(dados)
    df['data_compra'] = pd.to_datetime(df['data_compra'])
    return df


def calcular_rfv(df: pd.DataFrame, data_referencia: pd.Timestamp) -> pd.DataFrame:
    rfv_df = df.groupby('cliente_id').agg(
        **{
            'Recência (R)': ('data_compra', lambda x: (data_referencia - x.max()).days),
            'Frequência (F)': ('cliente_id', 'count'),
            'Valor (V)': ('valor_compra', 'sum'),
        }
    ).reset_index()
    return rfv_df


def calcular_quartis(rfv_df: pd.DataFrame) -> pd.DataFrame:
    r_labels = [4, 3, 2, 1]
    f_labels = [1, 2, 3, 4]
    v_labels = [1, 2, 3, 4]

    rfv_seg = rfv_df.copy()
    try:
        rfv_seg['R_Quartil'] = pd.qcut(rfv_seg['Recência (R)'], q=4, labels=r_labels, duplicates='drop')
        rfv_seg['F_Quartil'] = pd.qcut(rfv_seg['Frequência (F)'], q=4, labels=f_labels, duplicates='drop')
        rfv_seg['V_Quartil'] = pd.qcut(rfv_seg['Valor (V)'], q=4, labels=v_labels, duplicates='drop')
    except Exception:
        rfv_seg['R_Quartil'] = pd.qcut(rfv_seg['Recência (R)'].rank(method='first'), q=4, labels=r_labels)
        rfv_seg['F_Quartil'] = pd.qcut(rfv_seg['Frequência (F)'].rank(method='first'), q=4, labels=f_labels)
        rfv_seg['V_Quartil'] = pd.qcut(rfv_seg['Valor (V)'].rank(method='first'), q=4, labels=v_labels)

    rfv_seg['RFV_Score'] = (
        rfv_seg['R_Quartil'].astype(str) +
        rfv_seg['F_Quartil'].astype(str) +
        rfv_seg['V_Quartil'].astype(str)
    )
    return rfv_seg


def classificar_segmento(rfv_score: str) -> str:
    s = str(rfv_score)
    if s >= "444": return "Melhores Clientes"
    elif s >= "344": return "Clientes Fiéis"
    elif s >= "244": return "Potenciais Fidelizados"
    elif s >= "144": return "Novos Clientes"
    elif s >= "443": return "Clientes em Risco"
    elif s >= "333": return "Clientes Adormecidos"
    elif s >= "222": return "Quase Perdidos"
    else: return "Clientes Perdidos"


def get_rfv_segmentado(data_referencia: Optional[date] = None) -> pd.DataFrame:
    df = gerar_dados_exemplo()
    ref = pd.to_datetime(data_referencia) if data_referencia else df['data_compra'].max() + pd.Timedelta(days=1)
    rfv_df = calcular_rfv(df, ref)
    rfv_seg = calcular_quartis(rfv_df)
    rfv_seg['Segmento'] = rfv_seg['RFV_Score'].apply(classificar_segmento)
    return rfv_seg


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", summary="Status da API")
def root():
    return {"status": "online", "descricao": "API RFV - Segmentação de Clientes", "versao": "1.0.0"}


@app.get("/api/metrics", summary="Métricas gerais do RFV")
def get_metrics(data_referencia: Optional[date] = Query(default=None, description="Data de referência (YYYY-MM-DD)")):
    """
    Retorna métricas consolidadas de Recência, Frequência e Valor.
    """
    rfv = get_rfv_segmentado(data_referencia)
    return {
        "total_clientes": int(rfv['cliente_id'].nunique()),
        "recencia_media_dias": round(float(rfv['Recência (R)'].mean()), 1),
        "frequencia_media": round(float(rfv['Frequência (F)'].mean()), 1),
        "valor_medio": round(float(rfv['Valor (V)'].mean()), 2),
        "valor_total": round(float(rfv['Valor (V)'].sum()), 2),
        "data_referencia": str(data_referencia or "automática"),
    }


@app.get("/api/segmentos", summary="Contagem de clientes por segmento")
def get_segmentos(data_referencia: Optional[date] = Query(default=None)):
    """
    Retorna a distribuição de clientes por segmento RFV.
    """
    rfv = get_rfv_segmentado(data_referencia)
    contagem = rfv['Segmento'].value_counts().reset_index()
    contagem.columns = ['segmento', 'quantidade']
    total = len(rfv)
    resultado = []
    for _, row in contagem.iterrows():
        resultado.append({
            "segmento": row['segmento'],
            "quantidade": int(row['quantidade']),
            "percentual": round(row['quantidade'] / total * 100, 1)
        })
    return {"segmentos": resultado, "total_clientes": total}


@app.get("/api/clientes", summary="Lista de clientes com scores RFV")
def get_clientes(
    segmento: Optional[str] = Query(default=None, description="Filtrar por segmento"),
    limite: int = Query(default=50, le=500, description="Máximo de registros retornados"),
    data_referencia: Optional[date] = Query(default=None)
):
    """
    Retorna lista de clientes com seus scores RFV e segmento.
    Permite filtrar por segmento e limitar o número de registros.
    """
    rfv = get_rfv_segmentado(data_referencia)

    if segmento:
        rfv = rfv[rfv['Segmento'].str.contains(segmento, case=False, na=False)]
        if rfv.empty:
            raise HTTPException(status_code=404, detail=f"Nenhum cliente encontrado para o segmento '{segmento}'")

    rfv = rfv.head(limite)

    clientes = []
    for _, row in rfv.iterrows():
        clientes.append({
            "cliente_id": int(row['cliente_id']),
            "recencia_dias": int(row['Recência (R)']),
            "frequencia": int(row['Frequência (F)']),
            "valor_total": round(float(row['Valor (V)']), 2),
            "rfv_score": str(row['RFV_Score']),
            "segmento": row['Segmento'],
        })
    return {"total": len(clientes), "clientes": clientes}


@app.get("/api/clientes/{cliente_id}", summary="Dados de um cliente específico")
def get_cliente(cliente_id: int, data_referencia: Optional[date] = Query(default=None)):
    """
    Retorna os dados RFV de um cliente pelo ID.
    """
    rfv = get_rfv_segmentado(data_referencia)
    cliente = rfv[rfv['cliente_id'] == cliente_id]

    if cliente.empty:
        raise HTTPException(status_code=404, detail=f"Cliente {cliente_id} não encontrado")

    row = cliente.iloc[0]
    return {
        "cliente_id": int(row['cliente_id']),
        "recencia_dias": int(row['Recência (R)']),
        "frequencia": int(row['Frequência (F)']),
        "valor_total": round(float(row['Valor (V)']), 2),
        "rfv_score": str(row['RFV_Score']),
        "segmento": row['Segmento'],
    }


@app.get("/api/quartis", summary="Limites dos quartis RFV")
def get_quartis(data_referencia: Optional[date] = Query(default=None)):
    """
    Retorna os valores dos quartis (Q1, Q2, Q3) de cada dimensão RFV.
    """
    rfv = get_rfv_segmentado(data_referencia)
    return {
        "recencia": {
            "q1": round(float(rfv['Recência (R)'].quantile(0.25)), 1),
            "q2_mediana": round(float(rfv['Recência (R)'].quantile(0.50)), 1),
            "q3": round(float(rfv['Recência (R)'].quantile(0.75)), 1),
        },
        "frequencia": {
            "q1": round(float(rfv['Frequência (F)'].quantile(0.25)), 1),
            "q2_mediana": round(float(rfv['Frequência (F)'].quantile(0.50)), 1),
            "q3": round(float(rfv['Frequência (F)'].quantile(0.75)), 1),
        },
        "valor": {
            "q1": round(float(rfv['Valor (V)'].quantile(0.25)), 2),
            "q2_mediana": round(float(rfv['Valor (V)'].quantile(0.50)), 2),
            "q3": round(float(rfv['Valor (V)'].quantile(0.75)), 2),
        },
    }
