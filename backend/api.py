import os
import sqlite3
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

# Caminho para o banco de dados
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'deputados.db')

app = FastAPI(title="Deputados API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Deputados ────────────────────────────────────────────────────────────────

@app.get("/deputados")
def buscar_deputados(q: Optional[str] = Query(None, min_length=2)):
    """Busca deputados pelo nome ou retorna todos se q for omitido."""
    conn = get_conn()
    try:
        if q:
            rows = conn.execute(
                "SELECT * FROM deputados WHERE nome LIKE ? ORDER BY nome LIMIT 50",
                (f"%{q}%",)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM deputados ORDER BY nome LIMIT 200"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/deputados/{id_deputado}")
def perfil_deputado(id_deputado: str):
    """Retorna o perfil completo de um deputado pelo ID."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM deputados WHERE id = ?", (id_deputado,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Deputado não encontrado")
        return dict(row)
    finally:
        conn.close()


@app.get("/deputados/{id_deputado}/detalhes")
def detalhes_deputado(id_deputado: str):
    """Retorna detalhes íntimos (nascimento, escolaridade, etc) de um deputado."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM deputados_detalhes WHERE id = ?", (id_deputado,)
        ).fetchone()
        if not row:
            # Tentar ver se o deputado existe em 'deputados' para não dar 404 enganoso
            dep_existe = conn.execute("SELECT 1 FROM deputados WHERE id=?", (id_deputado,)).fetchone()
            if dep_existe:
                return {} # Deputado existe mas sem detalhes processados
            raise HTTPException(status_code=404, detail="Deputado não possui detalhes carregados")
        return dict(row)
    finally:
        conn.close()


# ─── Despesas ─────────────────────────────────────────────────────────────────

@app.get("/deputados/{id_deputado}/despesas")
def despesas_por_tipo(id_deputado: str, idLegislatura: Optional[str] = None):
    """Retorna gastos agrupados por tipo de despesa para um deputado."""
    conn = get_conn()
    try:
        query = """
            SELECT tipoDespesa, somaValorLiquido, rankGastador, rankEconomizador, idLegislatura
            FROM deputados_despesas_legislatura
            WHERE idDeputado = ?
        """
        params = [id_deputado]
        if idLegislatura:
            query += " AND idLegislatura = ?"
            params.append(idLegislatura)
        query += " ORDER BY somaValorLiquido DESC"

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/deputados/{id_deputado}/despesas/mensal")
def despesas_mensais(id_deputado: str, idLegislatura: Optional[str] = None):
    """Retorna evolução mensal de gastos de um deputado."""
    conn = get_conn()
    try:
        query = """
            SELECT idLegislatura, ano, mes, tipoDespesa, somaValorLiquido
            FROM deputados_despesas_legislatura_mensal
            WHERE idDeputado = ?
        """
        params = [id_deputado]
        if idLegislatura:
            query += " AND idLegislatura = ?"
            params.append(idLegislatura)
        query += " ORDER BY ano, mes"

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/deputados/{id_deputado}/despesas/zscore")
def zscore_deputado(id_deputado: str, idLegislatura: Optional[str] = None):
    """
    Calcula o Z-Score do deputado comparado à média geral,
    baseado na tabela deputados_despesas_legislatura_condensado.
    """
    conn = get_conn()
    try:
        query = "SELECT idDeputado, valorTotal FROM deputados_despesas_legislatura_condensado"
        params = []
        if idLegislatura:
            query += " WHERE idLegislatura = ?"
            params.append(idLegislatura)

        rows = conn.execute(query, params).fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="Sem dados consolidados para calcular Z-Score")

        todos_valores = np.array([r["valorTotal"] for r in rows], dtype=float)
        media = float(np.mean(todos_valores))
        desvio = float(np.std(todos_valores))

        # Buscar o valor do deputado solicitado
        query_dep = "SELECT valorTotal FROM deputados_despesas_legislatura_condensado WHERE idDeputado = ?"
        params_dep = [id_deputado]
        if idLegislatura:
            query_dep += " AND idLegislatura = ?"
            params_dep.append(idLegislatura)

        row_dep = conn.execute(query_dep, params_dep).fetchone()
        if not row_dep:
            raise HTTPException(status_code=404, detail="Deputado não encontrado nos dados consolidados")

        valor_deputado = float(row_dep["valorTotal"])
        z = (valor_deputado - media) / desvio if desvio > 0 else 0.0

        # Classificação semântica
        if abs(z) <= 1:
            classificacao = "Normal"
        elif abs(z) <= 2:
            classificacao = "Atencao"
        else:
            classificacao = "Outlier"

        return {
            "idDeputado": id_deputado,
            "valorTotal": valor_deputado,
            "media": media,
            "desvioPadrao": desvio,
            "zScore": round(z, 4),
            "classificacao": classificacao,
            "totalDeputadosAvaliados": len(todos_valores),
        }
    finally:
        conn.close()


# ─── Ranking ──────────────────────────────────────────────────────────────────

@app.get("/ranking")
def ranking_gastos(idLegislatura: Optional[str] = None, limite: int = 50):
    """Retorna o ranking dos maiores gastadores."""
    conn = get_conn()
    try:
        query = """
            SELECT c.idDeputado, d.nome, d.siglaPartido, d.siglaUf, d.urlFoto,
                   c.valorTotal, c.rankGastador, c.idLegislatura
            FROM deputados_despesas_legislatura_condensado c
            LEFT JOIN deputados d ON d.id = c.idDeputado
        """
        params = []
        if idLegislatura:
            query += " WHERE c.idLegislatura = ?"
            params.append(idLegislatura)
        query += " ORDER BY c.rankGastador ASC LIMIT ?"
        params.append(limite)

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ─── Legislaturas disponíveis ─────────────────────────────────────────────────

@app.get("/legislaturas")
def listar_legislaturas():
    """Lista todos os IDs de legislatura disponíveis no banco."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT idLegislatura FROM deputados ORDER BY idLegislatura"
        ).fetchall()
        return [r["idLegislatura"] for r in rows if r["idLegislatura"]]
    finally:
        conn.close()
