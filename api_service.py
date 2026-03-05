import requests

def buscar_deputados(idlegislatura):
    """
    Consome a API da Câmara dos Deputados para obter a lista de deputados.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados?idLegislatura={idlegislatura}&ordem=ASC&ordenarPor=nome"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a API: {e}")
        return None

def buscar_deputado_detalhado(id):
    """
    Consome a API da Câmara dos Deputados para obter detalhes de um deputado específico.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{id}"
    headers = {'accept': 'application/json'}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
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
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
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
    # A primeira chamada usa os params, as subsequentes usam a URL do link 'next'
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    dados_pagina = response.json()
    
    todas_despesas.extend(dados_pagina.get('dados', []))
    
    # Loop de paginação
    links = dados_pagina.get('links', [])
    proxima_url = next((link['href'] for link in links if link['rel'] == 'next'), None)
    
    while proxima_url:
        response = requests.get(proxima_url, headers=headers)
        response.raise_for_status()
        dados_pagina = response.json()
        
        todas_despesas.extend(dados_pagina.get('dados', []))
        
        links = dados_pagina.get('links', [])
        proxima_url = next((link['href'] for link in links if link['rel'] == 'next'), None)

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
