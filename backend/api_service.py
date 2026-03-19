import requests
import time
import csv
import io
import zipfile
import os
import json
from bs4 import BeautifulSoup

# Mecanismo de tentativa
def realizar_requisicao_com_retry(url, headers=None, params=None, max_retries=3, timeout=30, ignore_errors=None):
    """
    Realiza uma requisição GET com mecanismo de retentativa em caso de erros temporários (como 504).
    """
    if ignore_errors is None:
        ignore_errors = []
        
    tentativa = 0
    while tentativa < max_retries:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            tentativa += 1
            status_code = getattr(e.response, 'status_code', 'N/A')
            
            # Verificação de erros ignoráveis
            if isinstance(e, requests.exceptions.HTTPError) and status_code in ignore_errors:
                return None

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

# deputados.json (id deputado | legislatura | nome | siglaPartido | siglaUf | urlFoto)
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

# deputado_detalhado.json (id deputado | nome civil | cpf | gabinete | situacao | condicao eleitoral | data inicio |  rede social
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

# deputado_funcionario.json (id deputado | nome do funcionário | cargo | data início)
def buscar_deputado_funcionarios():
    """
    Consome a API da Câmara dos Deputados para obter a lista de funcionários dos deputados.
    Extrai o idDeputado a partir do final da uriLotacao.
    URL: http://dadosabertos.camara.leg.br/arquivos/funcionarios/json/funcionarios.json
    """
    url = "http://dadosabertos.camara.leg.br/arquivos/funcionarios/json/funcionarios.json"
    headers = {'accept': 'application/json'}
    
    try:
        response = realizar_requisicao_com_retry(url, headers=headers)
        dados = response.json()
        
        # Processa cada funcionário para extrair o idDeputado da uriLotacao
        if dados and 'dados' in dados:
            for funcionario in dados['dados']:
                uri = funcionario.get('uriLotacao')
                if uri and isinstance(uri, str):
                    # Pega a parte após a última barra
                    partes = uri.rstrip('/').split('/')
                    if partes:
                        # Mantém o ID como string conforme solicitado
                        funcionario['idDeputado'] = partes[-1]
                else:
                    funcionario['idDeputado'] = None
        
        return dados
    except Exception as e:
        print(f"Erro ao buscar funcionários dos deputados: {e}")
        return None

# deputado_despesas.json ()
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

# 
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


#eventos.json
def buscar_eventos(data_inicio, data_fim, itens=100, ordem='DESC', ordenar_por='dataHoraInicio'):
    """
    Busca TODOS os eventos em um intervalo de datas, percorrendo automaticamente todas as páginas da API.
    """
    url = "https://dadosabertos.camara.leg.br/api/v2/eventos"
    headers = {'accept': 'application/json'}
    params = {
        'dataInicio': data_inicio,
        'dataFim': data_fim,
        'itens': itens,
        'ordem': ordem,
        'ordenarPor': ordenar_por
    }

    todos_eventos = []
    pagina = 1

    try:
        print(f"Buscando eventos de {data_inicio} até {data_fim}...")
        response = realizar_requisicao_com_retry(url, headers=headers, params=params)
        dados_pagina = response.json()
        eventos_pagina = dados_pagina.get('dados', [])
        todos_eventos.extend(eventos_pagina)
        print(f"Página {pagina} carregada: {len(eventos_pagina)} eventos encontrados. Total acumulado: {len(todos_eventos)}")

        links = dados_pagina.get('links', [])
        proxima_url = next((link['href'] for link in links if link['rel'] == 'next'), None)

        while proxima_url:
            pagina += 1
            response = realizar_requisicao_com_retry(proxima_url, headers=headers)
            dados_pagina = response.json()
            eventos_pagina = dados_pagina.get('dados', [])
            todos_eventos.extend(eventos_pagina)
            print(f"Página {pagina} carregada: {len(eventos_pagina)} eventos encontrados. Total acumulado: {len(todos_eventos)}")

            links = dados_pagina.get('links', [])
            proxima_url = next((link['href'] for link in links if link['rel'] == 'next'), None)

        print(f"Busca finalizada. Total de eventos: {len(todos_eventos)}")
    except Exception as e:
        print(f"Erro ao buscar eventos entre {data_inicio} e {data_fim}: {e}")
        if not todos_eventos:
            return None

    return {"dados": todos_eventos}

def buscar_detalhe_evento(id_evento):
    """
    Busca os detalhes completos de um evento específico pelo seu ID.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/eventos/{id_evento}"
    headers = {'accept': 'application/json'}

    try:
        response = realizar_requisicao_com_retry(url, headers=headers)
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar detalhes do evento {id_evento}: {e}")
        return None

def buscar_presencas_evento(id_evento):
    """
    Busca a lista de deputados presentes em um evento específico.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/eventos/{id_evento}/deputados"
    headers = {'accept': 'application/json'}

    try:
        response = realizar_requisicao_com_retry(url, headers=headers)
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar presenças do evento {id_evento}: {e}")
        return None

def buscar_votacoes_evento(id_evento):
    """
    Busca a lista de votações ocorridas em um evento específico.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/eventos/{id_evento}/votacoes"
    headers = {'accept': 'application/json'}

    try:
        response = realizar_requisicao_com_retry(url, headers=headers)
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar votações do evento {id_evento}: {e}")
        return None

def buscar_orientacoes_votacao(id_votacao):
    """
    Busca as orientações de bancada de uma votação específica pelo seu ID.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/votacoes/{id_votacao}/orientacoes"
    headers = {'accept': 'application/json'}

    try:
        response = realizar_requisicao_com_retry(url, headers=headers)
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar orientações da votação {id_votacao}: {e}")
        return None

def buscar_votos_votacao(id_votacao):
    """
    Busca os votos individuais de uma votação específica pelo seu ID.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/votacoes/{id_votacao}/votos"
    headers = {'accept': 'application/json'}

    try:
        response = realizar_requisicao_com_retry(url, headers=headers)
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar votos da votação {id_votacao}: {e}")
        return None

def buscar_proposicoes_arquivo_anual(ano):
    """
    Faz o download do arquivo consolidado anual de proposições no formato JSON.
    URL: http://dadosabertos.camara.leg.br/arquivos/proposicoes/json/proposicoes-{ano}.json
    """
    url = f"http://dadosabertos.camara.leg.br/arquivos/proposicoes/json/proposicoes-{ano}.json"

    try:
        response = realizar_requisicao_com_retry(url, ignore_errors=[404])
        if response is None:
            return None
        dados = response.json()
        total = len(dados.get('dados', []))
        return dados
    except Exception:
        return None

def buscar_autores_proposicao(id_proposicao):
    """
    Consome a API da Câmara dos Deputados para obter os autores de uma proposição específica.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id_proposicao}/autores"
    headers = {'accept': 'application/json'}
    
    try:
        response = realizar_requisicao_com_retry(url, headers=headers)
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar autores da proposição {id_proposicao}: {e}")
        return None

def buscar_frentes_deputado(id_deputado):
    """
    Consome a API da Câmara dos Deputados para obter as frentes parlamentares de um deputado específico.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{id_deputado}/frentes"
    headers = {'accept': 'application/json'}
    
    try:
        response = realizar_requisicao_com_retry(url, headers=headers)
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar frentes do deputado {id_deputado}: {e}")
        return None

def buscar_orgaos_deputado(id_deputado):
    """
    Consome a API da Câmara dos Deputados para obter os órgãos de um deputado específico.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{id_deputado}/orgaos?ordem=ASC&ordenarPor=dataInicio"
    headers = {'accept': 'application/json'}
    
    try:
        response = realizar_requisicao_com_retry(url, headers=headers)
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar órgãos do deputado {id_deputado}: {e}")
        return None

def buscar_tipos_proposicoes():
    """
    Consome a API de referências para obter todas as siglas de tipos de proposições.
    """
    url = "https://dadosabertos.camara.leg.br/api/v2/referencias/proposicoes/siglaTipo"
    headers = {'accept': 'application/json'}

    try:
        response = realizar_requisicao_com_retry(url, headers=headers)
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar tipos de proposições: {e}")
        return None

def buscar_tipos_eventos(eventos_pontuacao=None):
    """
    Consome a API de referências para obter todos os tipos de eventos e adiciona
    a marcação de obrigatorio baseada na lista de dicionários EVENTOS_PONTUACAO.
    Regra:
    - 1 se obrigatoriedade for "obrigatório"
    - 2 se obrigatoriedade for diferente de "obrigatório"
    - 0 se não estiver catalogado em EVENTOS_PONTUACAO
    """
    url = "https://dadosabertos.camara.leg.br/api/v2/referencias/eventos/codTipoEvento"
    headers = {'accept': 'application/json'}

    # Cria um mapeamento de cod para obrigatoriedade e descrição para busca rápida
    mapeamento = {}
    if eventos_pontuacao:
        for item in eventos_pontuacao:
            cod = str(item.get('cod'))
            status = 1 if item.get('obrigatoriedade') == 'obrigatório' else 2
            descricao_param = item.get('descricao', '')
            mapeamento[cod] = {'status': status, 'descricao': descricao_param}

    try:
        response = realizar_requisicao_com_retry(url, headers=headers)
        dados_tipagem = response.json()
        
        if 'dados' in dados_tipagem:
            for tipo in dados_tipagem['dados']:
                cod = str(tipo.get('cod'))
                info_param = mapeamento.get(cod)

                if info_param:
                    tipo['obrigatorio'] = info_param['status']
                    # Se a descrição estiver vazia na API, preenche com a do parâmetro
                    if not tipo.get('descricao') or tipo.get('descricao') == "":
                        tipo['descricao'] = info_param['descricao']
                else:
                    tipo['obrigatorio'] = 0
                    
        return dados_tipagem
    except Exception as e:
        print(f"Erro ao buscar tipos de eventos: {e}")
        return None

def buscar_despesas_consolidadas(anos_legislatura=None):
    """
    Baixa os arquivos ZIP de despesas consolidadas por ano, extrai o JSON e remove o ZIP.
    URL: https://www.camara.leg.br/cotas/Ano-{ano}.json.zip
    """
    if not anos_legislatura:
        return None

    diretorio_raw = os.path.join(os.path.dirname(__file__), "raw")
    if not os.path.exists(diretorio_raw):
        os.makedirs(diretorio_raw)

    resultados = []

    for ano in anos_legislatura:
        url = f"https://www.camara.leg.br/cotas/Ano-{ano}.json.zip"
        caminho_zip = os.path.join(diretorio_raw, f"Ano-{ano}.json.zip")
        
        print(f"Baixando despesas consolidadas de {ano}...")
        try:
            response = realizar_requisicao_com_retry(url, timeout=120)
            if response:
                with open(caminho_zip, 'wb') as f:
                    f.write(response.content)
                
                # Extrair o ZIP
                with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
                    # O arquivo dentro costuma ter o mesmo nome do zip sem a extensão .zip
                    arquivos_no_zip = zip_ref.namelist()
                    zip_ref.extractall(diretorio_raw)
                    print(f"  Extraído: {arquivos_no_zip}")
                
                # Renomear o arquivo extraído para despesas-{ano}.json
                if arquivos_no_zip:
                    caminho_original = os.path.join(diretorio_raw, arquivos_no_zip[0])
                    caminho_novo = os.path.join(diretorio_raw, f"despesas-{ano}.json")
                    
                    # Se o nome já for o esperado, não faz nada, senão renomeia
                    if caminho_original != caminho_novo:
                        if os.path.exists(caminho_novo):
                            os.remove(caminho_novo)
                        os.rename(caminho_original, caminho_novo)
                        print(f"  Renomeado de {arquivos_no_zip[0]} para despesas-{ano}.json")
                
                # Remover o ZIP
                os.remove(caminho_zip)
                print(f"  Arquivo ZIP removido. JSON mantido em {diretorio_raw}")
                
                # Opcional: Ler o conteúdo do arquivo renomeado
                caminho_json = os.path.join(diretorio_raw, f"despesas-{ano}.json")
                if os.path.exists(caminho_json):
                    with open(caminho_json, 'r', encoding='utf-8') as f:
                        dados = json.load(f)
                        # Se os dados forem uma lista direta, envolvemos em {'dados': ...}
                        if isinstance(dados, list):
                            dados = {'dados': dados}
                        resultados.append(dados)
            else:
                print(f"  Arquivo para o ano {ano} não encontrado (404).")
        except Exception as e:
            print(f"  Erro ao processar despesas de {ano}: {e}")

    # Retorna o consolidado de todos os anos processados
    consolidado = {"dados": []}
    for r in resultados:
        if 'dados' in r:
            consolidado['dados'].extend(r['dados'])
    
    return consolidado



# Não funciona | Não consigo linkar o deputado ao seu funcionário.
def buscar_funcionarios_salarios(anos_legislatura=None):
    """
    Faz web scraping no site da Câmara dos Deputados para obter os relatórios 
    consolidados de remuneração mensal dos servidores, navegando por todos os anos e meses.
    
    Parâmetros:
        anos_legislatura: lista de anos (str) para filtrar. Se None, baixa todos.
    
    Retorna todos os registros consolidados em um único dicionário com chave 'dados'.
    """
    url_base = "https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao/relatorios-consolidados-por-ano-e-mes"
    
    todos_registros = []
    
    try:
        # 1. Buscar a lista de anos na página principal (com paginação)
        print("Buscando lista de anos disponíveis...")
        anos_links = []
        url_pagina = url_base
        
        while url_pagina:
            response = realizar_requisicao_com_retry(url_pagina, timeout=60)
            soup = BeautifulSoup(response.text, 'lxml')
            content = soup.select_one('#content-core')
            
            if not content:
                print("Não foi possível encontrar o conteúdo da página.")
                break
            
            ul = content.select_one('ul')
            if ul:
                for a in ul.find_all('a'):
                    href = a.get('href', '')
                    texto = a.text.strip()
                    # Filtra apenas links de anos (texto numérico)
                    if texto.isdigit():
                        anos_links.append({'ano': texto, 'url': href})
            
            # Verifica se há próxima página
            url_pagina = None
            for a in content.find_all('a'):
                if 'b_start' in str(a.get('href', '')) and 'Próximo' in a.text:
                    url_pagina = a.get('href')
                    break
        
        print(f"Anos encontrados no site: {[a['ano'] for a in anos_links]}")
        
        # Filtra apenas os anos da legislatura, se informado
        if anos_legislatura:
            anos_filtro = [str(a) for a in anos_legislatura]
            anos_links = [a for a in anos_links if a['ano'] in anos_filtro]
            print(f"Anos filtrados pela legislatura: {[a['ano'] for a in anos_links]}")
        
        # 2. Para cada ano, navegar e buscar os CSVs
        for info_ano in anos_links:
            ano = info_ano['ano']
            url_ano = info_ano['url']
            print(f"Processando ano {ano}...")
            
            try:
                response_ano = realizar_requisicao_com_retry(url_ano, timeout=60)
                soup_ano = BeautifulSoup(response_ano.text, 'lxml')
                
                # Buscar todos os links CSV na tabela
                tabela = soup_ano.select_one('table')
                if not tabela:
                    print(f"  Tabela não encontrada para o ano {ano}. Pulando...")
                    continue
                
                rows = tabela.find_all('tr')
                for row in rows:
                    # Pegar o texto do mês (primeira coluna)
                    colunas = row.find_all('td')
                    if not colunas:
                        continue
                    
                    mes_texto = colunas[0].text.strip()
                    
                    # Encontrar o link CSV na linha
                    csv_link = None
                    for a in row.find_all('a'):
                        href = a.get('href', '')
                        texto_link = a.text.strip().upper()
                        if texto_link == 'CSV' or href.lower().endswith('-csv'):
                            csv_link = href
                            break
                    
                    if not csv_link:
                        continue
                    
                    print(f"  Baixando CSV: {mes_texto}...")
                    
                    try:
                        response_csv = realizar_requisicao_com_retry(csv_link, timeout=120)
                        if not response_csv:
                            print(f"  Falha ao baixar CSV de {mes_texto}.")
                            continue
                        
                        # Detectar encoding
                        conteudo = response_csv.content.decode('utf-8', errors='replace')
                        
                        # Parse do CSV (separador ;)
                        leitor = csv.DictReader(io.StringIO(conteudo), delimiter=';')
                        
                        for registro in leitor:
                            registro['ano'] = ano
                            registro['mes'] = mes_texto
                            todos_registros.append(registro)
                        
                    except Exception as e_csv:
                        print(f"  Erro ao processar CSV de {mes_texto}: {e_csv}")
                        continue
                        
            except Exception as e_ano:
                print(f"Erro ao processar ano {ano}: {e_ano}")
                continue
        
        print(f"Scraping finalizado. Total de registros: {len(todos_registros)}")
        return {"dados": todos_registros}
        
    except Exception as e:
        print(f"Erro no scraping de salários dos funcionários: {e}")
        if todos_registros:
            return {"dados": todos_registros}
        return None
    










    # Exemplo de teste: Busca gastos do deputado Arthur Lira (id 204379)
  