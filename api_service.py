import requests
import time

def realizar_requisicao_com_retry(url, headers=None, params=None, max_retries=3, timeout=30):
    """
    Realiza uma requisição GET com mecanismo de retentativa em caso de erros temporários (como 504).
    """
    tentativa = 0
    while tentativa < max_retries:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            tentativa += 1
            status_code = getattr(e.response, 'status_code', 'N/A')
            
            # Se for erro 4xx (exceto 429), provavelmente não adianta tentar de novo
            if isinstance(e, requests.exceptions.HTTPError) and 400 <= status_code < 500 and status_code != 429:
                print(f"Erro fatal {status_code}: {e}")
                raise e
            
            if tentativa < max_retries:
                espera = tentativa * 2  # Exponential backoff simples
                print(f"Erro na requisição ({status_code}). Tentativa {tentativa}/{max_retries}. Aguardando {espera}s...")
                time.sleep(espera)
            else:
                print(f"Limite de tentativas atingido para a URL: {url}")
                raise e
    return None

def buscar_deputados(idlegislatura):
    """
    Consome a API da Câmara dos Deputados para obter a lista de deputados.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados?idLegislatura={idlegislatura}&ordem=ASC&ordenarPor=nome"
    
    try:
        response = realizar_requisicao_com_retry(url)
        return response.json()
    except Exception as e:
        print(f"Erro ao acessar a API: {e}")
        return None

def buscar_deputado_detalhado(id):
    """
    Consome a API da Câmara dos Deputados para obter detalhes de um deputado específico.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{id}"
    headers = {'accept': 'application/json'}
    
    try:
        response = realizar_requisicao_com_retry(url, headers=headers)
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar detalhes do deputado {id}: {e}")
        return None

def buscar_despesas(id_deputado, id_legislatura=None, itens=100, ordem='ASC', ordenar_por='ano'):
    """
    Busca as despesas de um deputado específico com parâmetros opcionais.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{id_deputado}/despesas"
    headers = {'accept': 'application/json'}
    params = {
        'itens': itens,
        'ordem': ordem,
        'ordenarPor': ordenar_por
    }
    
    if id_legislatura:
        params['idLegislatura'] = id_legislatura

    try:
        response = realizar_requisicao_com_retry(url, headers=headers, params=params)
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar despesas do deputado {id_deputado}: {e}")
        return None

def buscar_todas_despesas_paginado(id_deputado, id_legislatura=None, itens=100):
    """
    Busca TODAS as despesas de um deputado, percorrendo automaticamente todas as páginas da API.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{id_deputado}/despesas"
    headers = {'accept': 'application/json'}
    params = {
        'idLegislatura': id_legislatura,
        'itens': itens,
        'ordem': 'ASC',
        'ordenarPor': 'ano'
    }
    # Remove None
    params = {k: v for k, v in params.items() if v is not None}
    
    todas_despesas = []
    
    try:
        # A primeira chamada usa os params, as subsequentes usam a URL do link 'next'
        response = realizar_requisicao_com_retry(url, headers=headers, params=params)
        dados_pagina = response.json()
        
        todas_despesas.extend(dados_pagina.get('dados', []))
        
        # Loop de pagination
        links = dados_pagina.get('links', [])
        proxima_url = next((link['href'] for link in links if link['rel'] == 'next'), None)
        
        while proxima_url:
            response = realizar_requisicao_com_retry(proxima_url, headers=headers)
            dados_pagina = response.json()
            
            todas_despesas.extend(dados_pagina.get('dados', []))
            
            links = dados_pagina.get('links', [])
            proxima_url = next((link['href'] for link in links if link['rel'] == 'next'), None)
    except Exception as e:
         print(f"Erro ao buscar despesas paginadas do deputado {id_deputado}: {e}")
         # Retorna o que conseguiu até agora ou None se falhou na primeira
         if not todas_despesas:
             return None

    return {"dados": todas_despesas}

def buscar_todos_deputados_consolidado(formato="json"):
    """
    Faz o download do arquivo consolidado de todos os deputados em um formato específico.
    Formatos suportados: csv, xlsx, ods, json, xml.
    """
    formatos_suportados = ["csv", "xlsx", "ods", "json", "xml"]
    if formato not in formatos_suportados:
        print(f"Formato '{formato}' não suportado. Use um dos seguintes: {formatos_suportados}")
        return None

    url = f"https://dadosabertos.camara.leg.br/arquivos/deputados/{formato}/deputados.{formato}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Se for JSON, retorna o objeto Python, caso contrário retorna o conteúdo bruto (bytes)
        if formato == "json":
            return response.json()
        return response.content
        
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar arquivo consolidado ({formato}): {e}")
        return None

def buscar_todas_legislaturas_consolidado(formato="json"):
    """
    Faz o download do arquivo consolidado de todas as legislaturas em um formato específico.
    Formatos suportados: csv, xlsx, ods, json, xml.
    """
    formatos_suportados = ["csv", "xlsx", "ods", "json", "xml"]
    if formato not in formatos_suportados:
        print(f"Formato '{formato}' não suportado. Use um dos seguintes: {formatos_suportados}")
        return None

    url = f"https://dadosabertos.camara.leg.br/arquivos/legislaturas/{formato}/legislaturas.{formato}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        if formato == "json":
            return response.json()
        return response.content
        
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar legislaturas consolidadas ({formato}): {e}")
        return None
