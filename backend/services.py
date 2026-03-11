import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from api_service import (
    buscar_deputados, 
    buscar_deputado_detalhado, 
    buscar_todas_despesas_paginado, 
    buscar_eventos, 
    buscar_detalhe_evento,
    buscar_presencas_evento,
    buscar_votacoes_evento,
    buscar_orientacoes_votacao,
    buscar_votos_votacao,
    buscar_proposicoes_arquivo_anual,
    buscar_autores_proposicao,
    buscar_frentes_deputado,
    buscar_orgaos_deputado
)
from file_handler import obter_dados_com_cache_por_arquivo, salvar_em_json

def agregar_votos_votacoes_por_ids(base_ids, max_workers=10):
    """
    Busca os votos individuais de cada votação de forma concorrente.
    Recebe diretamente uma lista de IDs de votação.
    Compatível com o sistema de cache por ID do main.
    """
    print(f"Buscando votos para {len(base_ids)} votação(ões) com {max_workers} threads...")
    todos_votos = []

    def task_votos(id_votacao):
        try:
            resultado = buscar_votos_votacao(id_votacao)
            votos_lista = []
            if resultado and 'dados' in resultado:
                for voto in resultado['dados']:
                    voto['idVotacao'] = id_votacao
                    votos_lista.append(voto)
            return votos_lista
        except Exception as e:
            print(f"Erro na tarefa de votos para {id_votacao}: {e}")
            return []

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(task_votos, vid): vid for vid in base_ids}

            try:
                for future in as_completed(futures):
                    vid = futures[future]
                    try:
                        votos_retornados = future.result()
                        todos_votos.extend(votos_retornados)
                    except Exception as e:
                        print(f"Erro ao processar votos da votação {vid}: {e}")
            except KeyboardInterrupt:
                print("\nInterrupção detectada! Cancelando tarefas de votos pendentes...")
                for f in futures:
                    f.cancel()
                raise
    except KeyboardInterrupt:
        print("Finalizando busca de votos precocemente devido à interrupção.")
        # Retorna o que já foi coletado em vez de quebrar tudo, 
        # ou pode relançar se o main.py souber lidar.
        # Aqui vamos relançar para manter o comportamento original de parada, 
        # mas agora o executor fechará corretamente.
        raise

    print(f"Busca de votos finalizada. Total: {len(todos_votos)}")
    return {"dados": todos_votos}

def agregar_orientacoes_votacoes(eventos_votacoes, max_workers=20):
    """
    Busca as orientações de bancada para cada votação de forma concorrente.
    Recebe a lista de eventos com suas votações (estrutura de eventos_votacoes.json).
    """
    if not eventos_votacoes or 'dados' not in eventos_votacoes:
        print("Erro: JSON de votações inválido.")
        return None

    # Extrai todos os IDs únicos de votações
    votos_ids = set()
    for evento in eventos_votacoes['dados']:
        for votacao in evento.get('votacoes', []):
            if votacao.get('id'):
                votos_ids.add(votacao['id'])

    print(f"Buscando orientações para {len(votos_ids)} votação(ões) com {max_workers} threads...")

    todas_orientacoes = []

    def task_orientacoes(id_votacao):
        resultado = buscar_orientacoes_votacao(id_votacao)
        orientacoes_voto = []
        if resultado and 'dados' in resultado:
            for orientacao in resultado['dados']:
                orientacao['idVotacao'] = id_votacao
                orientacoes_voto.append(orientacao)
        return orientacoes_voto

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(task_orientacoes, vid): vid for vid in votos_ids}
        
        for future in as_completed(futures):
            vid = futures[future]
            try:
                orientacoes_retornadas = future.result()
                todas_orientacoes.extend(orientacoes_retornadas)
                # print(f"Votação {vid}: {len(orientacoes_retornadas)} orientação(ões) carregada(s).")
            except Exception as e:
                print(f"Erro ao processar orientações da votação {vid}: {e}")

    print(f"Busca de orientações finalizada. Total: {len(todas_orientacoes)}")
    return {"dados": todas_orientacoes}

def agregar_orientacoes_votacoes_por_ids(base_ids, max_workers=20):
    """
    Versão do agregador que recebe diretamente uma lista de IDs de votação.
    Compatível com o sistema de cache por ID do main.
    """
    print(f"Buscando orientações para {len(base_ids)} votação(ões) com {max_workers} threads...")
    todas_orientacoes = []

    def task_orientacoes(id_votacao):
        try:
            resultado = buscar_orientacoes_votacao(id_votacao)
            orientacoes_voto = []
            if resultado and 'dados' in resultado:
                for orientacao in resultado['dados']:
                    orientacao['idVotacao'] = id_votacao
                    orientacoes_voto.append(orientacao)
            return orientacoes_voto
        except Exception as e:
            print(f"Erro na tarefa de orientações para {id_votacao}: {e}")
            return []

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(task_orientacoes, vid): vid for vid in base_ids}
            
            try:
                for future in as_completed(futures):
                    try:
                        orientacoes_retornadas = future.result()
                        todas_orientacoes.extend(orientacoes_retornadas)
                    except Exception as e:
                        print(f"Erro ao processar orientações: {e}")
            except KeyboardInterrupt:
                print("\nInterrupção detectada! Cancelando tarefas de orientações...")
                for f in futures:
                    f.cancel()
                raise
    except KeyboardInterrupt:
        raise

    return {"dados": todas_orientacoes}

def agregar_autores_proposicoes_por_ids(base_ids, max_workers=10):
    """
    Busca os autores de cada proposição de forma concorrente.
    Recebe uma lista de IDs de proposição.
    """
    print(f"Buscando autores para {len(base_ids)} proposição(ões) com {max_workers} threads...")
    todos_autores = []

    def task_autores(id_proposicao):
        try:
            resultado = buscar_autores_proposicao(id_proposicao)
            autores_lista = []
            if resultado and 'dados' in resultado:
                for autor in resultado['dados']:
                    autor['idProposicao'] = id_proposicao
                    
                    uri = autor.get('uri', '')
                    if uri and '/deputados/' in uri:
                        id_responsavel = uri.split('/')[-1]
                        if id_responsavel.isdigit():
                            autor['idResponsavel'] = int(id_responsavel)
                        else:
                            autor['idResponsavel'] = None
                    else:
                        autor['idResponsavel'] = None
                        
                    autores_lista.append(autor)
            return autores_lista
        except Exception as e:
            print(f"Erro na tarefa de autores para {id_proposicao}: {e}")
            return []

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(task_autores, pid): pid for pid in base_ids}

            try:
                for future in as_completed(futures):
                    pid = futures[future]
                    try:
                        autores_retornados = future.result()
                        todos_autores.extend(autores_retornados)
                    except Exception as e:
                        print(f"Erro ao processar autores da proposição {pid}: {e}")
            except KeyboardInterrupt:
                print("\nInterrupção detectada! Cancelando tarefas de autores...")
                for f in futures:
                    f.cancel()
                raise
    except KeyboardInterrupt:
        raise

    print(f"Busca de autores finalizada. Total: {len(todos_autores)}")
    return {"dados": todos_autores}

def agregar_frentes_deputados_por_ids(base_ids, max_workers=10):
    """
    Busca as frentes parlamentares de cada deputado de forma concorrente.
    Recebe uma lista de IDs de deputado.
    """
    print(f"Buscando frentes para {len(base_ids)} deputado(s) com {max_workers} threads...")
    todas_frentes = []

    def task_frentes(id_deputado):
        try:
            resultado = buscar_frentes_deputado(id_deputado)
            frentes_lista = []
            if resultado and 'dados' in resultado:
                for frente in resultado['dados']:
                    frente['idDeputado'] = id_deputado
                    frentes_lista.append(frente)
            return frentes_lista
        except Exception as e:
            print(f"Erro na tarefa de frentes para {id_deputado}: {e}")
            return []

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(task_frentes, did): did for did in base_ids}

            try:
                for future in as_completed(futures):
                    did = futures[future]
                    try:
                        frentes_retornadas = future.result()
                        todas_frentes.extend(frentes_retornadas)
                    except Exception as e:
                        print(f"Erro ao processar frentes do deputado {did}: {e}")
            except KeyboardInterrupt:
                print("\nInterrupção detectada! Cancelando tarefas de frentes...")
                for f in futures:
                    f.cancel()
                raise
    except KeyboardInterrupt:
        raise

    print(f"Busca de frentes finalizada. Total: {len(todas_frentes)}")
    return {"dados": todas_frentes}

def agregar_orgaos_deputados_por_ids(base_ids, max_workers=10):
    """
    Busca os órgãos de cada deputado de forma concorrente.
    Recebe uma lista de IDs de deputado.
    """
    print(f"Buscando órgãos para {len(base_ids)} deputado(s) com {max_workers} threads...")
    todos_orgaos = []

    def task_orgaos(id_deputado):
        try:
            resultado = buscar_orgaos_deputado(id_deputado)
            orgaos_lista = []
            if resultado and 'dados' in resultado:
                for orgao in resultado['dados']:
                    orgao['idDeputado'] = id_deputado
                    orgaos_lista.append(orgao)
            return orgaos_lista
        except Exception as e:
            print(f"Erro na tarefa de órgãos para {id_deputado}: {e}")
            return []

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(task_orgaos, did): did for did in base_ids}

            try:
                for future in as_completed(futures):
                    did = futures[future]
                    try:
                        orgaos_retornados = future.result()
                        todos_orgaos.extend(orgaos_retornados)
                    except Exception as e:
                        print(f"Erro ao processar órgãos do deputado {did}: {e}")
            except KeyboardInterrupt:
                print("\nInterrupção detectada! Cancelando tarefas de órgãos...")
                for f in futures:
                    f.cancel()
                raise
    except KeyboardInterrupt:
        raise

    print(f"Busca de órgãos finalizada. Total: {len(todos_orgaos)}")
    return {"dados": todos_orgaos}

def agregar_despesas_deputados(lista_ids_deputados, ids_legislaturas=None, max_workers=10):
    """
    Busca todas as despesas para uma lista de IDs de deputados de forma concorrente.
    Se `ids_legislaturas` for fornecido (lista), busca apenas despesas dessas legislaturas.
    """
    if isinstance(lista_ids_deputados, int):
        lista_ids_deputados = [lista_ids_deputados]
        
    if not lista_ids_deputados:
        print("Aviso: Lista de IDs de deputados está vazia.")
        return {"dados": []}

    if isinstance(ids_legislaturas, int):
        ids_legislaturas = [ids_legislaturas]

    legislaturas_para_buscar = ids_legislaturas if ids_legislaturas else [None]

    # Cria todas as combinações (id_deputado, id_legislatura) para processar
    tarefas = [
        (id_dep, id_leg)
        for id_dep in lista_ids_deputados
        for id_leg in legislaturas_para_buscar
    ]

    total_tarefas = len(tarefas)
    print(f"Iniciando agregação concorrente de despesas: {len(lista_ids_deputados)} deputados x {len(legislaturas_para_buscar)} legislatura(s) = {total_tarefas} tarefa(s) com {max_workers} threads...")

    todas_despesas_consolidadas = []

    def buscar_despesas_tarefa(id_deputado, id_legislatura):
        resultado = buscar_todas_despesas_paginado(id_deputado, id_legislatura=id_legislatura)
        despesas = []
        if resultado and 'dados' in resultado:
            for despesa in resultado['dados']:
                despesa['idDeputadoDono'] = id_deputado
            despesas = resultado['dados']
        return despesas

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_tarefa = {
                executor.submit(buscar_despesas_tarefa, id_dep, id_leg): (id_dep, id_leg)
                for id_dep, id_leg in tarefas
            }

            concluidos = 0
            try:
                for future in as_completed(future_to_tarefa):
                    concluidos += 1
                    id_dep, id_leg = future_to_tarefa[future]
                    try:
                        despesas = future.result()
                        todas_despesas_consolidadas.extend(despesas)
                    except Exception as exc:
                        print(f"\nErro ao buscar despesas do deputado {id_dep} (leg {id_leg}): {exc}")

                    if concluidos % 10 == 0 or concluidos == total_tarefas:
                        print(f"Progresso: {concluidos}/{total_tarefas} tarefas concluídas...", end='\r')
            except KeyboardInterrupt:
                print("\nInterrupção detectada! Cancelando tarefas de despesas pendentes...")
                for f in future_to_tarefa:
                    f.cancel()
                raise
    except KeyboardInterrupt:
        raise

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

def agregar_detalhes_deputados(dados_deputados, max_workers=20):
    """
    Coordena a busca de detalhes para uma lista de deputados de forma concorrente,
    removendo IDs duplicados antes da busca.
    """
    lista_crua = dados_deputados.get('dados', [])
    
    deputados_unicos = {d['id']: d for d in lista_crua}.values()
    lista_dep = list(deputados_unicos)
    total = len(lista_dep)
    
    if total == 0:
        return {"dados": []}

    print(f"Iniciando busca concorrente de detalhes para {total} deputados únicos com {max_workers} threads...")
    
    todos_detalhes = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {executor.submit(buscar_deputado_detalhado, dep['id']): dep['id'] for dep in lista_dep}

        concluidos = 0
        for future in as_completed(future_to_id):
            concluidos += 1
            id_deputado = future_to_id[future]
            try:
                detalhes = future.result()
                if detalhes and 'dados' in detalhes:
                    todos_detalhes.append(detalhes['dados'])
            except Exception as exc:
                print(f"\nErro no deputado {id_deputado}: {exc}")

            if concluidos % 10 == 0 or concluidos == total:
                print(f"Progresso: {concluidos}/{total} processados...", end='\r')

    print(f"\nBusca de detalhes concluída! Total coletado: {len(todos_detalhes)}")
    return {"dados": todos_detalhes}

def agregar_presencas_eventos(lista_ids_eventos, max_workers=10):
    """
    Busca a lista de presença (deputados) para cada ID de evento de forma concorrente.
    Retorna uma lista onde cada item contém o ID do evento e a lista de presentes.
    """
    total = len(lista_ids_eventos)
    if total == 0:
        return {"dados": []}

    print(f"Buscando presenças para {total} eventos com {max_workers} threads...")
    
    todos_resultados = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Criamos uma tarefa para cada ID de evento
        future_to_id = {executor.submit(buscar_presencas_evento, id_ev): id_ev for id_ev in lista_ids_eventos}

        concluidos = 0
        for future in as_completed(future_to_id):
            concluidos += 1
            id_ev = future_to_id[future]
            try:
                resultado = future.result()
                if resultado and 'dados' in resultado:
                    # Estrutura: {id_evento: X, presencas: [...]}
                    todos_resultados.append({
                        "idEvento": id_ev,
                        "presencas": resultado['dados']
                    })
            except Exception as exc:
                print(f"\nErro ao buscar presenças do evento {id_ev}: {exc}")

            if concluidos % 10 == 0 or concluidos == total:
                print(f"Progresso Presenças: {concluidos}/{total} processados...", end='\r')

    print(f"\nBusca de presenças concluída! Total de eventos com presença: {len(todos_resultados)}")
    return {"dados": todos_resultados}

def agregar_votacoes_eventos(lista_ids_eventos, max_workers=10):
    """
    Busca as votações ocorridas em cada ID de evento de forma concorrente.
    Retorna uma lista onde cada item contém o ID do evento e as votações.
    """
    total = len(lista_ids_eventos)
    if total == 0:
        return {"dados": []}

    print(f"Buscando votações para {total} eventos com {max_workers} threads...")
    
    todos_resultados = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {executor.submit(buscar_votacoes_evento, id_ev): id_ev for id_ev in lista_ids_eventos}

        concluidos = 0
        for future in as_completed(future_to_id):
            concluidos += 1
            id_ev = future_to_id[future]
            try:
                resultado = future.result()
                if resultado and 'dados' in resultado:
                    todos_resultados.append({
                        "idEvento": id_ev,
                        "votacoes": resultado['dados']
                    })
            except Exception as exc:
                print(f"\nErro ao buscar votações do evento {id_ev}: {exc}")

            if concluidos % 10 == 0 or concluidos == total:
                print(f"Progresso Votações: {concluidos}/{total} processados...", end='\r')

    print(f"\nBusca de votações concluída! Total de eventos com votações: {len(todos_resultados)}")
    return {"dados": todos_resultados}

def agregar_eventos_por_legislaturas(legislaturas_consolidado, limite_legislaturas=None, max_workers=10):
    """
    Busca todos os eventos para cada legislatura de forma concorrente,
    extraindo dataInicio e dataFim do JSON consolidado.
    """
    if not legislaturas_consolidado or 'dados' not in legislaturas_consolidado:
        print("Erro: JSON de legislaturas inválido.")
        return None

    legislaturas = legislaturas_consolidado['dados']

    # Determina a chave de ID usada no arquivo consolidado
    chave_id = 'idLegislatura' if legislaturas and 'idLegislatura' in legislaturas[0] else 'id'

    # Ordena da legislatura mais recente para a mais antiga
    legislaturas_ordenadas = sorted(legislaturas, key=lambda x: x.get(chave_id, 0), reverse=True)

    if limite_legislaturas:
        legislaturas_ordenadas = legislaturas_ordenadas[:limite_legislaturas]
        print(f"Limite ativado: Processando as {limite_legislaturas} legislaturas mais recentes.")

    print(f"Buscando eventos para {len(legislaturas_ordenadas)} legislatura(s) com {max_workers} threads...")

    todos_eventos = []

    def task_eventos(leg):
        id_leg = leg.get('idLegislatura') or leg.get('id')
        data_inicio = leg.get('dataInicio')
        data_fim = leg.get('dataFim')

        if not data_inicio or not data_fim:
            print(f"Legislatura {id_leg}: datas não encontradas, pulando...")
            return []

        resultado = buscar_eventos(data_inicio, data_fim)
        
        eventos_leg = []
        if resultado and 'dados' in resultado:
            for evento in resultado['dados']:
                evento['idLegislatura'] = id_leg
                eventos_leg.append(evento)
        return eventos_leg

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(task_eventos, leg): leg for leg in legislaturas_ordenadas}
        
        for future in as_completed(futures):
            leg = futures[future]
            id_leg = leg.get('idLegislatura') or leg.get('id')
            try:
                eventos_retornados = future.result()
                todos_eventos.extend(eventos_retornados)
                print(f"Legislatura {id_leg}: {len(eventos_retornados)} evento(s) carregado(s).")
            except Exception as exc:
                print(f"Erro ao processar legislatura {id_leg}: {exc}")

    print(f"\nTotal de eventos coletados: {len(todos_eventos)}")
    return {"dados": todos_eventos}

def agregar_detalhes_eventos_concorrente(lista_ids_eventos, max_workers=10):
    """
    Busca os detalhes completos de uma lista de IDs de eventos de forma concorrente.
    Retorna uma lista de resultados (dados do evento).
    """
    total = len(lista_ids_eventos)
    if total == 0:
        return []

    todos_detalhes = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {executor.submit(buscar_detalhe_evento, id_ev): id_ev for id_ev in lista_ids_eventos}
        
        concluidos = 0
        for future in as_completed(future_to_id):
            concluidos += 1
            id_ev = future_to_id[future]
            try:
                detalhes = future.result()
                if detalhes and 'dados' in detalhes:
                    todos_detalhes.append(detalhes['dados'])
            except Exception as exc:
                print(f"\nErro no ID {id_ev}: {exc}")
            
            if concluidos % 10 == 0 or concluidos == total:
                print(f"Progresso: {concluidos}/{total} processados... ", end='\r')

    return {"dados": todos_detalhes}

def agregar_proposicoes_por_legislaturas(legislaturas_consolidado, limite_legislaturas=None):
    """
    Baixa os arquivos consolidados anuais de proposições para cada ano coberto pelas
    legislaturas selecionadas. Cada ano é cacheado individualmente como
    'proposicoes-{ano}.json'. Ao final, combina todos os dados em uma única lista
    e salva o resultado consolidado em 'proposicoes.json'.
    """
    if not legislaturas_consolidado or 'dados' not in legislaturas_consolidado:
        print("Erro: JSON de legislaturas inválido.")
        return None

    legislaturas = legislaturas_consolidado['dados']

    chave_id = 'idLegislatura' if legislaturas and 'idLegislatura' in legislaturas[0] else 'id'

    legislaturas_ordenadas = sorted(legislaturas, key=lambda x: x.get(chave_id, 0), reverse=True)

    if limite_legislaturas:
        legislaturas_ordenadas = legislaturas_ordenadas[:limite_legislaturas]

    # Coleta todos os anos únicos cobertos pelas legislaturas selecionadas
    anos = set()
    ano_atual = 2026 # Ano atual conforme ambiente
    for leg in legislaturas_ordenadas:
        data_inicio = leg.get('dataInicio', '')
        data_fim = leg.get('dataFim', '')
        if data_inicio and data_fim:
            ano_inicio = int(data_inicio[:4])
            ano_fim = int(data_fim[:4])
            for ano in range(ano_inicio, ano_fim + 1):
                if ano <= ano_atual:
                    anos.add(ano)

    anos_ordenados = sorted(anos, reverse=True)

    todas_proposicoes = []

    for ano in anos_ordenados:
        resultado = obter_dados_com_cache_por_arquivo(
            f"proposicoes-{ano}.json",
            buscar_proposicoes_arquivo_anual,
            ano=ano
        )
        if resultado and 'dados' in resultado:
            todas_proposicoes.extend(resultado['dados'])

    consolidado = {"dados": todas_proposicoes}
    salvar_em_json(consolidado, "proposicoes.json")
    return consolidado

