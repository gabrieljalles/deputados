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

def visualizar_despesas_mensais(filtro=None, ano=None, mes=None, limite=20):
    """Exibe as top N despesas mensais no terminal, com filtros opcionais de nome, ano e mês."""
    if not os.path.exists(DB_PATH):
        print(f"Erro: Banco de dados não encontrado em {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    sql = '''
        SELECT 
            dm.ano, 
            dm.mes, 
            d.nome, 
            dm.tipoDespesa, 
            dm.somaValorLiquido, 
            dm.rankGastador, 
            dm.rankEconomizador
        FROM deputados_despesas_legislatura_mensal dm
        JOIN deputados d ON dm.idDeputado = d.id
        WHERE 1=1
    '''
    
    params = []
    if filtro:
        sql += " AND (d.nome LIKE ? OR d.id = ?)"
        params.append(f"%{filtro}%")
        params.append(str(filtro))
    
    if ano:
        sql += " AND dm.ano = ?"
        params.append(int(ano))
        
    if mes:
        sql += " AND dm.mes = ?"
        params.append(int(mes))
        
    sql += " ORDER BY dm.ano DESC, dm.mes DESC, dm.tipoDespesa ASC LIMIT ?"
    params.append(limite)
    
    try:
        cursor.execute(sql, params)
        resultados = cursor.fetchall()
        
        print("\n" + "="*125)
        contexto_filtro = []
        if filtro: contexto_filtro.append(f"Deputado: {filtro}")
        if ano: contexto_filtro.append(f"Ano: {ano}")
        if mes: contexto_filtro.append(f"Mês: {mes}")
        
        titulo = f"GASTOS MENSAIS"
        if contexto_filtro:
            titulo += f" ({' | '.join(contexto_filtro)})"
        else:
            titulo += f" (Top {limite})"
            
        print(titulo.center(125))
        print("-"*125)
        print(f"{'ANO':<5} | {'MÊS':<3} | {'NOME DO DEPUTADO':<25} | {'TIPO':<35} | {'VALOR (R$)':<12} | {'RANK G':<6} | {'RANK E':<6}")
        print("-"*125)
        
        for ano, mes, nome, tipo, valor, rank_g, rank_e in resultados:
            print(f"{ano:<5} | {mes:02d}  | {nome[:25]:<25} | {tipo[:35]:<35} | {valor:>12,.2f} | {rank_g:^6} | {rank_e:^6}")
            
        print("="*125 + "\n")
        
    except sqlite3.Error as e:
        print(f"Erro ao consultar despesas mensais: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    # Se houver --stats: estatísticas (média/DP)
    # Se houver --geral: gastos totais condensados por deputado
    # Se houver --mensal: gastos mensais por categoria
    # Caso contrário: gastos por categoria (com filtro opcional)
    
    if "--stats" in sys.argv:
        visualizar_estatisticas()
    elif "--geral" in sys.argv:
        # Pega o termo de busca se houver (ex: python visualizar_dados.py --geral "Lira")
        args_restantes = [a for a in sys.argv[1:] if a != "--geral"]
        termo = args_restantes[0] if args_restantes else None
        visualizar_gastos_gerais(filtro=termo)
    elif "--mensal" in sys.argv:
        # Pega o termo de busca se houver (ex: python visualizar_dados.py --mensal "Lira" 2024 10)
        args_restantes = [a for a in sys.argv[1:] if a != "--mensal"]
        
        termo = None
        ano = None
        mes = None
        
        # Filtra argumentos que parecem ano ou mês (números)
        f_args = []
        for arg in args_restantes:
            if arg.isdigit():
                if len(arg) == 4:
                    ano = arg
                elif len(arg) <= 2:
                    mes = arg
            else:
                termo = arg
                
        visualizar_despesas_mensais(filtro="Acácio Favacho", ano="2025", mes="09")
    else:
        termo = sys.argv[1] if len(sys.argv) > 1 else None
        visualizar_despesas_totais(filtro=termo)
