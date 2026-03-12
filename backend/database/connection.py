import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'deputados.db')

def get_connection():
    """Retorna uma conexão com o banco de dados SQLite."""
    return sqlite3.connect(DB_PATH)

def init_db():
    """Cria e inicializa as tabelas do banco de dados."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()

    # Tabela de Deputados
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deputados (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            siglaPartido TEXT,
            siglaUf TEXT,
            idLegislatura TEXT,
            urlFoto TEXT,
            email TEXT
        )
    ''')

    # Tabela de Despesas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS despesas (
            id_despesa INTEGER PRIMARY KEY AUTOINCREMENT,
            id_deputado TEXT,
            tipo_despesa TEXT,
            data_emissao TEXT,
            valor_documento REAL,
            valor_liquido REAL,
            FOREIGN KEY (id_deputado) REFERENCES deputados (id)
        )
    ''')

    # Tabela de Despesas Condensadas por Legislatura
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deputados_despesas_legislatura (
            id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
            idLegislatura TEXT,
            idDeputado TEXT,
            tipoDespesa TEXT,
            somaValorLiquido REAL,
            rankGastador INTEGER,
            rankEconomizador INTEGER,
            UNIQUE(idLegislatura, idDeputado, tipoDespesa)
        )
    ''')

    # Tabela de Despesas Condensadas GERAIS (Total por Deputado/Legislatura)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deputados_despesas_legislatura_condensado (
            id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
            idLegislatura TEXT,
            idDeputado TEXT,
            valorTotal REAL,
            rankGastador INTEGER,
            rankEconomizador INTEGER,
            UNIQUE(idLegislatura, idDeputado)
        )
    ''')

    # Tabela de Estatísticas de Gastos (Média e Desvio Padrão)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estatisticas_gastos (
            id_estatistica INTEGER PRIMARY KEY AUTOINCREMENT,
            idLegislatura TEXT,
            tipoEstudo TEXT, -- 'DP' (Desvio Padrão) ou 'MS' (Média Simples)
            tipoDespesa TEXT,
            valor REAL,
            UNIQUE(idLegislatura, tipoEstudo, tipoDespesa)
        )
    ''')

    # Outras tabelas podem ser adicionadas conforme você processe outros arquivos (ex: votações, eventos)

    conn.commit()
    conn.close()
    print(f"Banco de dados inicializado em: {DB_PATH}")

if __name__ == "__main__":
    init_db()
