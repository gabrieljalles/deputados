import sqlite3
import os
from database.connection import DB_PATH

def visualizar_despesas_totais(filtro=None, limite=20):
    """
    Exibe as top N despesas condensadas por legislatura/deputado no terminal.
    
    Args:
        filtro (str): Nome do deputado ou ID para filtrar.
        limite (int): Quantidade de registros para exibir.
    """
    if not os.path.exists(DB_PATH):
        print(f"Erro: Banco de dados não encontrado em {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Base da query com JOIN
    sql_base = '''
        SELECT 
            dl.idLegislatura, 
            d.nome, 
            dl.tipoDespesa, 
            dl.somaValorLiquido,
            dl.rankGastador,
            dl.rankEconomizador
        FROM deputados_despesas_legislatura dl
        JOIN deputados d ON dl.idDeputado = d.id
    '''
    
    params = []
    
    # Se houver filtro, adiciona a cláusula WHERE para Nome ou ID
    if filtro:
        sql_base += " WHERE (d.nome LIKE ? OR d.id = ?)"
        params.append(f"%{filtro}%")
        params.append(str(filtro))
        
    sql_base += " ORDER BY dl.somaValorLiquido DESC LIMIT ?"
    params.append(limite)
    
    try:
        cursor.execute(sql_base, params)
        resultados = cursor.fetchall()
        
        print("\n" + "="*110)
        titulo = f"TOP {limite} GASTOS" if not filtro else f"GASTOS PARA: {filtro}"
        print(f"{titulo.center(110)}")
        print("-"*110)
        print(f"{'LEG':<5} | {'NOME DO DEPUTADO':<25} | {'TIPO':<25} | {'VALOR (R$)':<12} | {'RANK GAST':<10} | {'RANK ECON':<10}")
        print("-"*110)
        
        for leg, nome, tipo, valor, rank_g, rank_e in resultados:
            rank_g = rank_g if rank_g is not None else "-"
            rank_e = rank_e if rank_e is not None else "-"
            print(f"{leg:<5} | {nome[:25]:<25} | {tipo[:25]:<25} | {valor:>12,.2f} | {rank_g:^10} | {rank_e:^10}")
            
        print("="*110 + "\n")
        
    except sqlite3.Error as e:
        print(f"Erro ao consultar o banco: {e}")
    finally:
        conn.close()

def visualizar_estatisticas():
    """Exibe os cálculos de Média (MS) e Desvio Padrão (DP) por tipo de despesa."""
    if not os.path.exists(DB_PATH):
        print(f"Erro: Banco de dados não encontrado em {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = '''
        SELECT idLegislatura, tipoEstudo, tipoDespesa, valor
        FROM estatisticas_gastos
        ORDER BY idLegislatura, tipoDespesa, tipoEstudo
    '''
    
    try:
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        print("\n" + "="*90)
        print(f"{'CÁLCULOS ESTATÍSTICOS (MÉDIA MS E DESVIO PADRÃO DP)'.center(90)}")
        print("-"*90)
        print(f"{'LEG':<5} | {'ESTUDO':<8} | {'TIPO DE DESPESA':<45} | {'VALOR (R$)':<15}")
        print("-"*90)
        
        for leg, estudo, tipo, valor in resultados:
            cor_estudo = "[MS]" if estudo == "MS" else "[DP]"
            print(f"{leg:<5} | {cor_estudo:<8} | {tipo[:45]:<45} | {valor:>15,.2f}")
            
        print("="*90 + "\n")
        
    except sqlite3.Error as e:
        print(f"Erro ao consultar estatísticas: {e}")
    finally:
        conn.close()

def visualizar_gastos_gerais(filtro=None, limite=20):
    """Exibe o somatório total de gastos por deputado, ignorando o tipo de despesa."""
    if not os.path.exists(DB_PATH):
        print(f"Erro: Banco de dados não encontrado em {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            dc.idLegislatura, 
            d.nome, 
            dc.valorTotal,
            dc.rankGastador,
            dc.rankEconomizador
        FROM deputados_despesas_legislatura_condensado dc
        JOIN deputados d ON dc.idDeputado = d.id
    '''
    
    params = []
    if filtro:
        query += " WHERE (d.nome LIKE ? OR d.id = ?)"
        params.append(f"%{filtro}%")
        params.append(str(filtro))
        
    query += " ORDER BY dc.valorTotal DESC LIMIT ?"
    params.append(limite)
    
    try:
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
        print("\n" + "="*110)
        titulo = f"RANKING GERAL DE GASTOS (TODAS AS CATEGORIAS)" if not filtro else f"GASTO GERAL TOTAL: {filtro}"
        print(f"{titulo.center(110)}")
        print("-"*110)
        print(f"{'LEG':<5} | {'NOME DO DEPUTADO':<35} | {'VALOR TOTAL (R$)':<18} | {'RANK GAST':<10} | {'RANK ECON':<10}")
        print("-"*110)
        
        for leg, nome, total, rank_g, rank_e in resultados:
            print(f"{leg:<5} | {nome[:35]:<35} | {total:>18,.2f} | {rank_g:^10} | {rank_e:^10}")
            
        print("="*110 + "\n")
        
    except sqlite3.Error as e:
        print(f"Erro ao consultar gastos gerais: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    # Se houver --stats: estatísticas (média/DP)
    # Se houver --geral: gastos totais condensados por deputado
    # Caso contrário: gastos por categoria (com filtro opcional)
    
    if "--stats" in sys.argv:
        visualizar_estatisticas()
    elif "--geral" in sys.argv:
        # Pega o termo de busca se houver (ex: python visualizar_dados.py --geral "Lira")
        args_restantes = [a for a in sys.argv[1:] if a != "--geral"]
        termo = args_restantes[0] if args_restantes else None
        visualizar_gastos_gerais(filtro=termo)
    else:
        termo = sys.argv[1] if len(sys.argv) > 1 else None
        visualizar_despesas_totais(filtro=termo)
