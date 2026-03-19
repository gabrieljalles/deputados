import json
import os
import statistics
from rich.console import Console
from .connection import get_connection

console = Console()

def popular_deputados():
    """Lê o arquivo raw/deputados.json e insere os dados no banco de dados."""
    caminho_json = os.path.join(os.path.dirname(__file__), '..', 'raw', 'deputados.json')
    
    if not os.path.exists(caminho_json):
        console.print(f"[bold red]Erro:[/bold red] Arquivo {caminho_json} não encontrado.")
        return

    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar se a tabela já tem dados
        cursor.execute("SELECT COUNT(*) FROM deputados")
        count = cursor.fetchone()[0]
        
        if count > 0:
            console.print(f"[bold blue]ℹ [deputados][/bold blue] Já populada com {count} registros (ignorado).")
            conn.close()
            return

        with open(caminho_json, 'r', encoding='utf-8') as f:
            dados = json.load(f).get('dados', [])
        
        # console.print(f"[yellow]→ Inserindo {len(dados)} deputados no banco...[/yellow]")
        for dep in dados:
            cursor.execute('''
                INSERT OR REPLACE INTO deputados (id, nome, siglaPartido, siglaUf, idLegislatura, urlFoto, email)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(dep.get('id')),
                dep.get('nome'),
                dep.get('siglaPartido'),
                dep.get('siglaUf'),
                str(dep.get('idLegislatura')),
                dep.get('urlFoto'),
                dep.get('email')
            ))
            
        conn.commit()
        conn.close()
        console.print(f"[bold green]✔ [deputados][/bold green] {len(dados)} novos registros inseridos.")
    except Exception as e:
        console.print(f"[bold red]Erro ao popular deputados:[/bold red] {e}")

def popular_despesas_legislatura():
    """Lê o arquivo raw/despesas_consolidadas.json, condensa e insere no banco."""
    caminho_json = os.path.join(os.path.dirname(__file__), '..', 'raw', 'despesas_consolidadas.json')
    
    if not os.path.exists(caminho_json):
        console.print(f"[bold red]Erro:[/bold red] Arquivo {caminho_json} não encontrado.")
        return

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Verificar se a tabela já tem dados
        cursor.execute("SELECT COUNT(*) FROM deputados_despesas_legislatura")
        count = cursor.fetchone()[0]
        
        if count > 0:
            console.print(f"[bold blue]ℹ [despesas][/bold blue] Já populada com {count} registros (ignorado).")
            conn.close()
            return

        with open(caminho_json, 'r', encoding='utf-8') as f:
            conteudo = json.load(f)
            # Detectado que a estrutura real é {"dados": [...lista de despesas...]}
            dados_brutos = conteudo.get('dados', [])
            
        # Dicionário para condensar: {(idLegislatura, idDeputado, tipoDespesa): soma}
        condensado = {}
        
        console.print(f"[yellow]→ Processando {len(dados_brutos)} registros brutos de despesas...[/yellow]")
        for d in dados_brutos:
            # Pegamos o idLegislatura se existir, senão usamos '57'
            id_leg = str(d.get('codigoLegislatura') or d.get('idLegislatura') or '57')
            id_dep = str(d.get('numeroDeputadoID') or d.get('idDeputadoDono') or d.get('idDeputado') or 'Desconhecido')
            # No arquivo consolidado (ZIP/JSON), o campo de categoria é 'descricao'
            tipo = d.get('descricao') or d.get('tipoDespesa') or 'Outros'
            valor = float(d.get('valorLiquido', 0) or 0)
            
            chave = (id_leg, id_dep, tipo)
            condensado[chave] = condensado.get(chave, 0) + valor
        
        # Inserção no banco com INSERT OR REPLACE para evitar duplicatas (chave única no connection.py)
        # O SQLite fará o UPDATE automático se a combinação (idLeg, idDep, tipo) já existir
        for (id_leg, id_dep_str, tipo), soma in condensado.items():
            cursor.execute('''
                INSERT OR REPLACE INTO deputados_despesas_legislatura 
                (idLegislatura, idDeputado, tipoDespesa, somaValorLiquido)
                VALUES (?, ?, ?, ?)
            ''', (id_leg, id_dep_str, tipo, soma))
            
        conn.commit()

        # --- NOVA LÓGICA DE RANKING ---
        console.print("[yellow]→ Calculando rankings (Gastador e Economizador) por tipo de despesa...[/yellow]")
        
        # 1. Pegar todos os tipos de despesa presentes
        cursor.execute("SELECT DISTINCT tipoDespesa, idLegislatura FROM deputados_despesas_legislatura")
        categorias = cursor.fetchall()
        
        for tipo, leg in categorias:
            # 2. Buscar todos os registros dessa categoria ordenados por valor desc para Gastador
            cursor.execute('''
                SELECT id_registro FROM deputados_despesas_legislatura 
                WHERE tipoDespesa = ? AND idLegislatura = ?
                ORDER BY somaValorLiquido DESC
            ''', (tipo, leg))
            ids_gastadores = cursor.fetchall()
            
            # 3. Atualizar rankGastador (descendente: maior valor = 1) e rankEconomizador (ascendente: maior valor = ultimo)
            total = len(ids_gastadores)
            for i, (id_reg,) in enumerate(ids_gastadores, 1):
                rank_gastador = i
                rank_economizador = (total - i) + 1 # O que gastou mais (1º gastador) será o último economizador
                
                cursor.execute('''
                    UPDATE deputados_despesas_legislatura 
                    SET rankGastador = ?, rankEconomizador = ?
                    WHERE id_registro = ?
                ''', (rank_gastador, rank_economizador, id_reg))

        conn.commit()
        conn.close()
        console.print(f"[bold green]✔ [despesas][/bold green] {len(condensado)} registros condensados inseridos.")
    except Exception as e:
        console.print(f"[bold red]Erro ao popular despesas:[/bold red] {e}")

def popular_despesas_totais_condensadas():
    """Lê do banco os gastos por tipo e gera o total geral por deputado na legislatura."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Verificar se a tabela já tem dados
        cursor.execute("SELECT COUNT(*) FROM deputados_despesas_legislatura_condensado")
        if cursor.fetchone()[0] > 0:
            console.print("[bold blue]ℹ [despesas_totais][/bold blue] Já populada (ignorado).")
            conn.close()
            return

        console.print("[yellow]→ Calculando gastos totais por deputado (Geral)...[/yellow]")
        
        # 1. Agrupar tudo por Deputado e Legislatura ignorando o tipo
        cursor.execute('''
            SELECT idLegislatura, idDeputado, SUM(somaValorLiquido) as total
            FROM deputados_despesas_legislatura
            GROUP BY idLegislatura, idDeputado
            ORDER BY total DESC
        ''')
        dados = cursor.fetchall()
        
        if not dados:
            console.print("[bold yellow]⚠ [despesas_totais][/bold yellow] Nenhum dado encontrado para condensar.")
            conn.close()
            return

        # 2. Inserir os totais e calcular rankings
        total_deputados = len(dados)
        for i, (leg, id_dep, total) in enumerate(dados, 1):
            rank_g = i
            rank_e = (total_deputados - i) + 1
            
            cursor.execute('''
                INSERT INTO deputados_despesas_legislatura_condensado 
                (idLegislatura, idDeputado, valorTotal, rankGastador, rankEconomizador)
                VALUES (?, ?, ?, ?, ?)
            ''', (leg, id_dep, total, rank_g, rank_e))

        conn.commit()
        conn.close()
        console.print(f"[bold green]✔ [despesas_totais][/bold green] {total_deputados} registros de gastos gerais populados.")
    except Exception as e:
        console.print(f"[bold red]Erro ao popular despesas totais:[/bold red] {e}")

def popular_estatisticas_gastos():
    """Calcula e popula a tabela de estatísticas (Média MS e Desvio Padrão DP)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Verificar se já existe cálculo para evitar reprocessamento desnecessário
        # (Aqui você pode decidir se quer recalcular sempre para garantir dados atualizados)
        cursor.execute("SELECT COUNT(*) FROM estatisticas_gastos")
        if cursor.fetchone()[0] > 0:
            console.print("[bold blue]ℹ [estatisticas][/bold blue] Já populada (ignorado).")
            conn.close()
            return

        # Busca todos os gastos condensados agrupados por legislatura e tipo de despesa
        cursor.execute('''
            SELECT idLegislatura, tipoDespesa, somaValorLiquido 
            FROM deputados_despesas_legislatura
        ''')
        dados = cursor.fetchall()

        if not dados:
            console.print("[bold yellow]⚠ [estatisticas][/bold yellow] Nenhuma despesa encontrada para calcular.")
            conn.close()
            return

        # Organizar dados em dicionário: {(idLeg, tipoDespesa): [valores]}
        agrupado = {}
        for id_leg, tipo, valor in dados:
            chave = (str(id_leg), tipo)
            if chave not in agrupado:
                agrupado[chave] = []
            agrupado[chave].append(valor)

        console.print("[yellow]→ Calculando estatísticas (Média e Desvio Padrão)...[/yellow]")
        
        for (id_leg, tipo), valores in agrupado.items():
            # Média Simples (MS)
            media = statistics.mean(valores)
            cursor.execute('''
                INSERT OR REPLACE INTO estatisticas_gastos (idLegislatura, tipoEstudo, tipoDespesa, valor)
                VALUES (?, ?, ?, ?)
            ''', (id_leg, 'MS', tipo, media))

            # Desvio Padrão (DP)
            # Necessário pelo menos 2 pontos para DP, senão é 0
            dp = statistics.stdev(valores) if len(valores) > 1 else 0
            cursor.execute('''
                INSERT OR REPLACE INTO estatisticas_gastos (idLegislatura, tipoEstudo, tipoDespesa, valor)
                VALUES (?, ?, ?, ?)
            ''', (id_leg, 'DP', tipo, dp))

        conn.commit()
        conn.close()
        console.print(f"[bold green]✔ [estatisticas][/bold green] Cálculos de DP e MS concluídos para {len(agrupado)} categorias.")
    except Exception as e:
        console.print(f"[bold red]Erro ao calcular estatísticas:[/bold red] {e}")

def popular_despesas_mensais():
    """Lê o arquivo raw/despesas_consolidadas.json, condensa por mês/ano e insere no banco."""
    caminho_json = os.path.join(os.path.dirname(__file__), '..', 'raw', 'despesas_consolidadas.json')
    
    if not os.path.exists(caminho_json):
        console.print(f"[bold red]Erro:[/bold red] Arquivo {caminho_json} não encontrado.")
        return

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Verificar se a tabela já tem dados
        cursor.execute("SELECT COUNT(*) FROM deputados_despesas_legislatura_mensal")
        count = cursor.fetchone()[0]
        
        if count > 0:
            console.print(f"[bold blue]ℹ [despesas_mensais][/bold blue] Já populada com {count} registros (ignorado).")
            conn.close()
            return

        with open(caminho_json, 'r', encoding='utf-8') as f:
            conteudo = json.load(f)
            dados_brutos = conteudo.get('dados', [])
            
        # Dicionário: {(idLeg, ano, mes, idDep, tipo): soma}
        condensado = {}
        
        console.print(f"[yellow]→ Processando {len(dados_brutos)} registros brutos para despesas mensais...[/yellow]")
        for d in dados_brutos:
            id_leg = str(d.get('codigoLegislatura') or d.get('idLegislatura') or '57')
            id_dep = str(d.get('numeroDeputadoID') or d.get('idDeputadoDono') or d.get('idDeputado') or 'Desconhecido')
            # No arquivo consolidado (ZIP/JSON), o campo de categoria é 'descricao'
            tipo = d.get('descricao') or d.get('tipoDespesa') or 'Outros'
            valor = float(d.get('valorLiquido', 0) or 0)
            ano = d.get('ano')
            mes = d.get('mes')
            
            if ano is None or mes is None:
                continue

            chave = (id_leg, ano, mes, id_dep, tipo)
            condensado[chave] = condensado.get(chave, 0) + valor
        
        for (id_leg, ano, mes, id_dep, tipo), soma in condensado.items():
            cursor.execute('''
                INSERT OR REPLACE INTO deputados_despesas_legislatura_mensal 
                (idLegislatura, ano, mes, idDeputado, tipoDespesa, somaValorLiquido)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (id_leg, ano, mes, id_dep, tipo, soma))
            
        conn.commit()

        console.print("[yellow]→ Calculando rankings mensais por categoria...[/yellow]")
        
        # Rankings por (idLegislatura, ano, mes, tipoDespesa)
        cursor.execute("SELECT DISTINCT idLegislatura, ano, mes, tipoDespesa FROM deputados_despesas_legislatura_mensal")
        categorias = cursor.fetchall()
        
        for leg, ano, mes, tipo in categorias:
            cursor.execute('''
                SELECT id_registro FROM deputados_despesas_legislatura_mensal 
                WHERE idLegislatura = ? AND ano = ? AND mes = ? AND tipoDespesa = ?
                ORDER BY somaValorLiquido DESC
            ''', (leg, ano, mes, tipo))
            ids_gastadores = cursor.fetchall()
            
            total = len(ids_gastadores)
            for i, (id_reg,) in enumerate(ids_gastadores, 1):
                rank_gastador = i
                rank_economizador = (total - i) + 1
                
                cursor.execute('''
                    UPDATE deputados_despesas_legislatura_mensal 
                    SET rankGastador = ?, rankEconomizador = ?
                    WHERE id_registro = ?
                ''', (rank_gastador, rank_economizador, id_reg))

        conn.commit()
        conn.close()
        console.print(f"[bold green]✔ [despesas_mensais][/bold green] {len(condensado)} registros mensais inseridos.")
    except Exception as e:
        console.print(f"[bold red]Erro ao popular despesas mensais:[/bold red] {e}")



