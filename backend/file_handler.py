import json
import os
import time

def obter_dados_com_cache_por_arquivo(nome_arquivo, funcao, diretorio="data", *args, **kwargs):
    """
    Verifica se um arquivo JSON existe.
    Se existir, carrega os dados do arquivo.
    Se não existir, executa a função, salva o resultado e o retorna.
    """
    if not os.path.exists(diretorio):
        os.makedirs(diretorio)
    
    caminho_completo = os.path.join(diretorio, nome_arquivo)
    
    if os.path.exists(caminho_completo):
        print(f"Arquivo '{nome_arquivo}' já existe em '{diretorio}'. Carregando dados locais...")
        try:
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Erro ao ler cache '{nome_arquivo}': {e}. Buscando dados novamente...")
    
    print(f"Buscando novos dados para '{nome_arquivo}'...")
    resultado = funcao(*args, **kwargs)
    
    # Validação genérica sugerida: Verifica se o resultado é válido e se contém a chave 'dados'
    # (Comum na API da Câmara)
    if not resultado:
        print(f"Erro: A função '{funcao.__name__}' não retornou dados para '{nome_arquivo}'.")
        return None

    # Opcional: Se for um dicionário e você espera que tenha 'dados', avisa se não tiver
    if isinstance(resultado, dict) and 'dados' not in resultado:
        print(f"Aviso: Dados obtidos para '{nome_arquivo}', mas a chave 'dados' não foi encontrada.")

    salvar_em_json(resultado, nome_arquivo, diretorio)
    
    return resultado

def salvar_em_json(dados, nome_arquivo, diretorio="data"):
    """
    Salva os dados fornecidos em um arquivo JSON em um diretório específico.
    """
    if not dados:
        print("Nenhum dado para salvar.")
        return

    # Garante que o diretório exista
    try:
        if not os.path.exists(diretorio):
            os.makedirs(diretorio)
            print(f"Diretório '{diretorio}' criado com sucesso.")
        
        # Caminho completo do arquivo
        caminho_completo = os.path.join(diretorio, nome_arquivo)
        
        with open(caminho_completo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
        print(f"Dados salvos com sucesso em '{caminho_completo}'")
        
    except (IOError, OSError) as e:
        print(f"Erro ao salvar o arquivo: {e}")

def obter_dados_com_cache_por_id(nome_arquivo, base_ids, funcao_busca_item, diretorio="data", checkpoint_intervalo=100, **kwargs):
    """
    Cache inteligente por ID.
    1. Lê os dados já salvos em 'nome_arquivo'.
    2. Identifica quais IDs de 'base_ids' ainda não foram processados.
    3. Busca apenas os faltantes usando 'funcao_busca_item'.
    4. Salva o progresso a cada 'checkpoint_intervalo'.
    """
    if not os.path.exists(diretorio):
        os.makedirs(diretorio)
    
    caminho_completo = os.path.join(diretorio, nome_arquivo)
    dados_existentes = []
    ids_processados = set()

    # Carrega o que já existe
    if os.path.exists(caminho_completo):
        try:
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
                dados_carregados = conteudo.get('dados', [])
                # Deduplica pelo campo de ID reconhecido ('id' ou 'idEvento')
                for item in dados_carregados:
                    id_item = item.get('id') if 'id' in item else item.get('idEvento')
                    if id_item is not None:
                        try:
                            id_item = int(id_item)
                        except (ValueError, TypeError):
                            pass
                        if id_item not in ids_processados:
                            ids_processados.add(id_item)
                            dados_existentes.append(item)
                    else:
                        dados_existentes.append(item)
            print(f"Cache por ID: {len(ids_processados)} registros carregados de '{nome_arquivo}'.")
        except Exception as e:
            print(f"Erro ao carregar cache por ID: {e}. Iniciando do zero.")

    # Converte os IDs da base para o mesmo tipo para comparação (int por segurança se a API usa int)
    base_ids_formatados = []
    for bid in base_ids:
        try:
            base_ids_formatados.append(int(bid))
        except (ValueError, TypeError):
            base_ids_formatados.append(bid)

    ids_faltantes = [id_item for id_item in base_ids_formatados if id_item not in ids_processados]
    
    if not ids_faltantes:
        print(f"Todos os {len(base_ids_formatados)} IDs já estão processados em '{nome_arquivo}'.")
        return {"dados": dados_existentes}

    print(f"Processando {len(ids_faltantes)} IDs faltantes (Total: {len(base_ids_formatados)})...")
    
    novos_dados = []
    total_faltantes = len(ids_faltantes)

    # Processa em lotes do tamanho do checkpoint_intervalo,
    # aproveitando a concorrência e salvando após cada lote
    for i in range(0, total_faltantes, checkpoint_intervalo):
        lote = ids_faltantes[i:i + checkpoint_intervalo]
        fim_lote = min(i + checkpoint_intervalo, total_faltantes)
        print(f"\n[{fim_lote}/{total_faltantes}] Buscando lote de {len(lote)} IDs...")

        try:
            resultado = funcao_busca_item(lote, **kwargs)
            if resultado and 'dados' in resultado:
                novos_dados.extend(resultado['dados'])
        except Exception as e:
            print(f"Erro ao processar lote [{i}:{fim_lote}]: {e}")

        print(f"[{fim_lote}/{total_faltantes}] Salvando checkpoint em '{nome_arquivo}'...")
        salvar_em_json({"dados": dados_existentes + novos_dados}, nome_arquivo, diretorio)

    return {"dados": dados_existentes + novos_dados}
