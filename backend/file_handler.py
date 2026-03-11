import json
import os
import time
from rich.console import Console
from rich.table import Table

console = Console()

def obter_dados_com_cache_por_arquivo(nome_arquivo, funcao, diretorio="raw", *args, **kwargs):
    """
    Verifica se um arquivo JSON existe.
    Se existir, carrega os dados do arquivo.
    Se não existir, executa a função, salva o resultado e o retorna.
    """
    if not os.path.exists(diretorio):
        os.makedirs(diretorio)
    
    caminho_completo = os.path.join(diretorio, nome_arquivo)
    
    if os.path.exists(caminho_completo):
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("[bold green]✔[/bold green]", f"{nome_arquivo}", "[bold green]Cache carregado[/bold green]")
        console.print(table)
        try:
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            console.print(f"[red]Erro ao ler cache '{nome_arquivo}': {e}. Buscando dados novamente...[/red]")
    
    console.print(f"[yellow]Buscando novos dados para '{nome_arquivo}'...[/yellow]")
    resultado = funcao(*args, **kwargs)
    
    # Validação genérica sugerida: Verifica se o resultado é válido e se contém a chave 'dados'
    # (Comum na API da Câmara)
    if resultado is None:
        # Silencia o erro para arquivos anuais de proposições que podem não existir ainda (404)
        if not nome_arquivo.startswith("proposicoes-"):
            print(f"Erro: A função '{funcao.__name__}' não retornou dados para '{nome_arquivo}'.")
        return None

    # Opcional: Se for um dicionário e você espera que tenha 'dados', avisa se não tiver
    if isinstance(resultado, dict) and 'dados' not in resultado:
        print(f"Aviso: Dados obtidos para '{nome_arquivo}', mas a chave 'dados' não foi encontrada.")

    salvar_em_json(resultado, nome_arquivo, diretorio)
    
    return resultado

def salvar_em_json(dados, nome_arquivo, diretorio="raw"):
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
        
    except (IOError, OSError) as e:
        print(f"Erro ao salvar o arquivo: {e}")

def obter_dados_com_cache_por_id(nome_arquivo, base_ids, funcao_busca_item, diretorio="raw", checkpoint_intervalo=100, campo_id="id", **kwargs):
    """
    Cache inteligente por ID.
    1. Lê os dados já salvos em 'nome_arquivo'.
    2. Identifica quais IDs de 'base_ids' ainda não foram processados.
    3. Busca apenas os faltantes usando 'funcao_busca_item'.
    4. Salva o progresso a cada 'checkpoint_intervalo'.

    IDs que retornaram sem dados também são registrados em 'ids_sem_dados' no JSON,
    evitando que sejam tentados novamente nas próximas execuções.

    Parâmetros:
        campo_id: nome do campo usado como chave de rastreamento nos itens salvos.
                  Padrão 'id'. Exemplos: 'idEvento', 'idVotacao'.
    """
    if not os.path.exists(diretorio):
        os.makedirs(diretorio)

    caminho_completo = os.path.join(diretorio, nome_arquivo)
    dados_existentes = []
    ids_processados = set()
    ids_sem_dados = set()

    # Carrega o que já existe
    if os.path.exists(caminho_completo):
        try:
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                conteudo = json.load(f)
                dados_carregados = conteudo.get('dados', [])
                for item in dados_carregados:
                    id_item = item.get(campo_id)
                    if id_item is not None:
                        try:
                            id_item = int(id_item)
                        except (ValueError, TypeError):
                            pass
                        ids_processados.add(id_item)
                    dados_existentes.append(item)
                # Carrega IDs que foram tentados mas não retornaram dados
                for id_vazio in conteudo.get('ids_sem_dados', []):
                    try:
                        id_vazio = int(id_vazio)
                    except (ValueError, TypeError):
                        pass
                    ids_sem_dados.add(id_vazio)
                    ids_processados.add(id_vazio)
            
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_row("[bold green]✔[/bold green]", f"{nome_arquivo}", "[bold green]Cache carregado[/bold green]")
            console.print(table)
        except Exception as e:
            console.print(f"[red]Erro ao carregar cache por ID: {e}. Iniciando do zero.[/red]")

    # Converte os IDs da base para o mesmo tipo para comparação
    base_ids_formatados = []
    for bid in base_ids:
        try:
            base_ids_formatados.append(int(bid))
        except (ValueError, TypeError):
            base_ids_formatados.append(bid)

    ids_faltantes = [bid for bid in base_ids_formatados if bid not in ids_processados]

    if not ids_faltantes:
        return {"dados": dados_existentes}

    console.print(f"[yellow]Processando {len(ids_faltantes)} IDs faltantes (Total: {len(base_ids_formatados)})...[/yellow]")

    novos_dados = []
    total_faltantes = len(ids_faltantes)

    for i in range(0, total_faltantes, checkpoint_intervalo):
        lote = ids_faltantes[i:i + checkpoint_intervalo]
        fim_lote = min(i + checkpoint_intervalo, total_faltantes)
        print(f"\n[{fim_lote}/{total_faltantes}] Buscando lote de {len(lote)} IDs...")

        ids_com_dados = set()
        try:
            resultado = funcao_busca_item(lote, **kwargs)
            if resultado and 'dados' in resultado:
                novos_dados.extend(resultado['dados'])
                # Descobre quais IDs do lote retornaram ao menos 1 item
                for item in resultado['dados']:
                    id_item = item.get(campo_id)
                    if id_item is not None:
                        try:
                            id_item = int(id_item)
                        except (ValueError, TypeError):
                            pass
                        ids_com_dados.add(id_item)
        except Exception as e:
            print(f"Erro ao processar lote [{i}:{fim_lote}]: {e}")

        # Registra IDs do lote que não retornaram nenhum dado
        for bid in lote:
            if bid not in ids_com_dados:
                ids_sem_dados.add(bid)

        print(f"[{fim_lote}/{total_faltantes}] Salvando checkpoint em '{nome_arquivo}'...")
        salvar_em_json(
            {"dados": dados_existentes + novos_dados, "ids_sem_dados": list(ids_sem_dados)},
            nome_arquivo,
            diretorio
        )

    return {"dados": dados_existentes + novos_dados}
