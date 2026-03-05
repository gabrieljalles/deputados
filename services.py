import time
from api_service import buscar_deputados, buscar_deputado_detalhado, buscar_todas_despesas_paginado

def agregar_despesas_deputados(lista_ids_deputados, ids_legislaturas=None):
    """
    Busca todas as despesas para uma lista de IDs de deputados.
    Se `ids_legislaturas` for fornecido (lista), busca apenas despesas dessas legislaturas.
    Caso contrário, busca todas as despesas disponíveis para cada deputado.
    """
    # Garante que lista_ids_deputados seja uma lista, mesmo que o usuário passe um único ID (int)
    if isinstance(lista_ids_deputados, int):
        lista_ids_deputados = [lista_ids_deputados]
        
    if not lista_ids_deputados:
        print("Aviso: Lista de IDs de deputados está vazia.")
        return {"dados": []}

    # Se ids_legislaturas for um número único, converte para lista
    if isinstance(ids_legislaturas, int):
        ids_legislaturas = [ids_legislaturas]

    print(f"Iniciando agregação de despesas para {len(lista_ids_deputados)} deputados...")
    
    todas_despesas_consolidadas = []
    total_deputados = len(lista_ids_deputados)
    
    # Tempo médio estimado por deputado (considerando paginação típica)
    segundos_por_deputado = 1.2 
    
    for i, id_deputado in enumerate(lista_ids_deputados, 1):
        # Cálculo de tempo restante
        restantes = total_deputados - i
        segundos_restantes = restantes * segundos_por_deputado
        min_restantes = int(segundos_restantes // 60)
        seg_restantes = int(segundos_restantes % 60)
        
        # Formata o tempo conforme solicitado: "3m 34s"
        tempo_str = f"{min_restantes}m {seg_restantes}s" if min_restantes > 0 else f"{seg_restantes}s"
        
        # Impressão no estilo carregamento (\r e flush)
        print(f"\r[{i}/{total_deputados}] Processando ID: {id_deputado} | Est. restante: {tempo_str}      ", end="", flush=True)
        
        # Se ids_legislaturas for None, busca tudo (histórico total)
        legislaturas_para_buscar = ids_legislaturas if ids_legislaturas else [None]
        
        for id_leg in legislaturas_para_buscar:
            resultado = buscar_todas_despesas_paginado(id_deputado, id_legislatura=id_leg)
            
            if resultado and 'dados' in resultado:
                for despesa in resultado['dados']:
                    despesa['idDeputadoDono'] = id_deputado
                todas_despesas_consolidadas.extend(resultado['dados'])
            
            time.sleep(0.05) 

    print(f"\nFinalizado! Total de registros de despesas: {len(todas_despesas_consolidadas)}")
    return {"dados": todas_despesas_consolidadas}

def agregar_deputados_por_legislaturas(legislaturas_consolidado, limite_legislaturas=10):
    """
    Extrai os IDs das legislaturas do JSON consolidado e busca 
    os deputados para cada uma, consolidando os resultados.
    O parâmetro `limite_legislaturas` permite definir quantas legislaturas 
    (das mais recentes para as mais antigas) serão processadas.
    """
    if not legislaturas_consolidado or 'dados' not in legislaturas_consolidado:
        print("Erro: JSON de legislaturas inválido.")
        return None

    # O arquivo consolidado usa 'idLegislatura' ao invés de 'id'
    ids_legislaturas = {leg.get('idLegislatura') or leg.get('id') for leg in legislaturas_consolidado['dados']}
    # Filtra None caso algum item não tenha nenhuma das chaves
    ids_legislaturas = {id_leg for id_leg in ids_legislaturas if id_leg is not None}
    
    # Ordena para processar da legislatura mais recente para a mais antiga
    ids_ordenados = sorted(ids_legislaturas, reverse=True)
    
    # Aplica o limite se fornecido
    if limite_legislaturas:
        ids_ordenados = ids_ordenados[:limite_legislaturas]
        print(f"Limite ativado: Processando as {limite_legislaturas} legislaturas mais recentes.")

    print(f"Iniciando serviço de agregação para {len(ids_ordenados)} legislaturas...")
    todos_deputados_lista = []
    
    for id_leg in ids_ordenados:
        print(f"Buscando deputados da legislatura {id_leg}...")
        resultado = buscar_deputados(id_leg)
        
        if resultado and 'dados' in resultado:
            todos_deputados_lista.extend(resultado['dados'])
        
        # Pausa para respeitar os limites da API (Rate Limiting)
        time.sleep(0.1)
    
    if not todos_deputados_lista:
        return None

    print(f"Total de deputados únicos encontrados: {len(todos_deputados_lista)}")
    return {"dados": list(todos_deputados_lista)}

def agregar_detalhes_deputados(dados_deputados):
    """
    Coordena a busca de detalhes para uma lista de deputados, removendo IDs duplicados antes da busca.
    Exibe o progresso e uma estimativa de tempo restante.
    """
    lista_crua = dados_deputados.get('dados', [])
    
    # Remove duplicados usando o ID como chave (preserva o último encontrado)
    deputados_unicos = {d['id']: d for d in lista_crua}.values()
    lista_dep = list(deputados_unicos)
    total = len(lista_dep)
    
    print(f"Iniciando busca de detalhes para {total} deputados únicos...")
    
    todos_detalhes = []
    tempo_medio_por_deputado = 0.6  # Estimativa aproximada (0.1 sleep + ~0.5 requisição)
    
    for i, deputado in enumerate(lista_dep, 1):
        id_deputado = deputado['id']
        
        # Cálculo da estimativa de tempo restante
        falta = total - i
        segundos_restantes = falta * tempo_medio_por_deputado
        minutos, segundos = divmod(int(segundos_restantes), 60)
        tempo_str = f"{minutos}m {segundos}s" if minutos > 0 else f"{segundos}s"
        
        print(f"[{i}/{total}] Processando ID: {id_deputado} | Est. restante: {tempo_str}", end='\r')
        
        detalhes = buscar_deputado_detalhado(id_deputado)
        
        if detalhes and 'dados' in detalhes:
            todos_detalhes.append(detalhes['dados'])
        
        time.sleep(0.1)
    
    print(f"\nBusca de detalhes concluída! Total coletado: {len(todos_detalhes)}")
    return todos_detalhes
