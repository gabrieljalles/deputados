import json
import os

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
