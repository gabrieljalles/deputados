from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from analise_estatistica import (
    calcular_desvio_padrao_gastos, 
    calcular_soma_total_valor_liquido, 
    media_por_deputado,
    plotar_gastos_deputados,
    gastos_por_tipo
)
from api_service import (
    buscar_todas_legislaturas_consolidado,
    buscar_tipos_eventos,
    buscar_tipos_proposicoes,
    buscar_deputado_funcionarios,
    buscar_funcionarios_salarios,
    buscar_despesas_consolidadas
)
from parametros.p_eventos_pontuacoes import EVENTOS_PONTUACAO
from file_handler import obter_dados_com_cache_por_arquivo, salvar_em_json, obter_dados_com_cache_por_id
from services import (
    agregar_deputados_por_legislaturas, 
    agregar_detalhes_deputados,
    agregar_despesas_deputados,
    agregar_eventos_por_legislaturas,
    agregar_detalhes_eventos_concorrente,
    agregar_orientacoes_votacoes_por_ids,
    agregar_presencas_eventos,
    agregar_votacoes_eventos,
    agregar_orientacoes_votacoes,
    agregar_votos_votacoes_por_ids,
    agregar_proposicoes_por_legislaturas,
    agregar_autores_proposicoes_por_ids,
    agregar_frentes_deputados_por_ids,
    agregar_orgaos_deputados_por_ids
)
from database.connection import init_db, limpar_banco
from database.populate import (
    popular_deputados, 
    popular_despesas_legislatura, 
    popular_despesas_totais_condensadas,
    popular_estatisticas_gastos,
    popular_despesas_mensais
)

console = Console()

import os
import json

# Parametros ----------------------------
limite_legislaturas = 1 # Define quantas legislaturas a partir da última deve ser baixado.
# ---------------------------------------


def executar_processo():
    console.print(Panel("[bold yellow]→ Iniciando processo de coleta de dados...[/bold yellow]", expand=False))
    
    # 0. Legislaturas Consolidadas
    legislaturas_consolidado = obter_dados_com_cache_por_arquivo(
        "legislaturas_consolidado.json",
        buscar_todas_legislaturas_consolidado,
        formato="json"
    )

    # 0.1 Tipos de Eventos
    tipos_eventos = obter_dados_com_cache_por_arquivo(
        "eventostipagem.json",
        buscar_tipos_eventos,
        eventos_pontuacao=EVENTOS_PONTUACAO
    )

    # 0.2 Tipos de Proposições
    tipos_proposicoes = obter_dados_com_cache_por_arquivo(
        "proposicoes_tipo.json",
        buscar_tipos_proposicoes
    )

    # 0.3 Funcionários dos Deputados
    deputado_funcionarios = obter_dados_com_cache_por_arquivo(
        "deputados_funcionarios.json",
        buscar_deputado_funcionarios
    )

    # 0.4 Salários dos Funcionários (Web Scraping)
    # Calcula os anos da legislatura com base em dataInicio e dataFim
    legislaturas_ordenadas = sorted(legislaturas_consolidado['dados'], key=lambda x: x['idLegislatura'], reverse=True)
    legislaturas_selecionadas = legislaturas_ordenadas[:limite_legislaturas]
    anos_legislatura = set()
    for leg in legislaturas_selecionadas:
        ano_inicio = int(leg['dataInicio'][:4])
        ano_fim = int(leg['dataFim'][:4])
        for ano in range(ano_inicio, ano_fim + 1):
            anos_legislatura.add(str(ano))
    anos_legislatura = sorted(anos_legislatura)
    
    funcionarios_salarios = obter_dados_com_cache_por_arquivo(
        "deputados_funcionarios_salarios.json",
        buscar_funcionarios_salarios,
        anos_legislatura=anos_legislatura
    )
    
    # 0.5 Despesas Consolidadas (ZIP/JSON)
    despesas_consolidadas = obter_dados_com_cache_por_arquivo(
        "despesas_consolidadas.json",
        buscar_despesas_consolidadas,
        anos_legislatura=anos_legislatura
    )
    
    # 1. Lista de Deputados por Legislatura (Agregada no services)
    deputados = obter_dados_com_cache_por_arquivo(
        "deputados.json",
        agregar_deputados_por_legislaturas,
        legislaturas_consolidado=legislaturas_consolidado,
        limite_legislaturas=limite_legislaturas
    )

    # 2. Detalhes dos Deputados (Agregada no services)
    deputados_detalhes = obter_dados_com_cache_por_arquivo(
        "deputados_detalhados.json",
        agregar_detalhes_deputados,
        dados_deputados=deputados
    )
    
    # Extraímos os IDs dos deputados encontrados acima
    ids_deputados = [d['id'] for d in deputados['dados']]
    
    # 3. Despesas dos Deputados (Apenas Legislatura 57)
    deputados_despesas = obter_dados_com_cache_por_arquivo(
        "deputados_despesas.json",
        agregar_despesas_deputados,
        lista_ids_deputados=ids_deputados,
    )

    # 4. Eventos por Legislatura
    eventos = obter_dados_com_cache_por_arquivo(
        "eventos.json",
        agregar_eventos_por_legislaturas,
        legislaturas_consolidado=legislaturas_consolidado,
        limite_legislaturas=limite_legislaturas
    )

    # 4.1 Presenças nos Eventos (Novo)
    # Extraímos IDs únicos de eventos coletados
    ids_eventos_lista = list({e['id'] for e in eventos.get('dados', []) if 'id' in e})
    
    eventos_presencas = obter_dados_com_cache_por_id(
        "evento_presencas.json",
        base_ids=ids_eventos_lista,
        funcao_busca_item=agregar_presencas_eventos,
        checkpoint_intervalo=500,
        campo_id="idEvento"
    )

    # 4.2 Votações nos Eventos (Novo)
    eventos_votacoes = obter_dados_com_cache_por_id(
        "eventos_votacoes.json",
        base_ids=ids_eventos_lista,
        funcao_busca_item=agregar_votacoes_eventos,
        checkpoint_intervalo=500,
        campo_id="idEvento"
    )

    # 4.3 Proposições por Legislatura (cache por ano em raw/proposicoes-{ano}.json)
    proposicoes = agregar_proposicoes_por_legislaturas(
        legislaturas_consolidado=legislaturas_consolidado,
        limite_legislaturas=limite_legislaturas
    )

    # 4.4 Extraímos IDs únicos de votações a partir de eventos_votacoes
    ids_votacoes_lista = []
    if eventos_votacoes and 'dados' in eventos_votacoes:
        for ev in eventos_votacoes['dados']:
            for vot in ev.get('votacoes', []):
                if vot.get('id'):
                    ids_votacoes_lista.append(vot['id'])

    # Remove duplicatas mantendo ordem
    ids_votacoes_lista = list(dict.fromkeys(ids_votacoes_lista))

    # 4.5 Votos das Votações
    votacao_votos = obter_dados_com_cache_por_id(
        "votacao_votos.json",
        base_ids=ids_votacoes_lista,
        funcao_busca_item=agregar_votos_votacoes_por_ids,
        checkpoint_intervalo=1000,
        campo_id="idVotacao"
    )

    # 4.6 Orientações de Votação
    votacao_orientacoes = obter_dados_com_cache_por_id(
        "votacao_orientacoes.json",
        base_ids=ids_votacoes_lista,
        funcao_busca_item=agregar_orientacoes_votacoes_por_ids,
        checkpoint_intervalo=1000,
        campo_id="idVotacao"
    )

    # 5. Autores das Proposições
    # Extraímos IDs únicos de proposições coletadas
    ids_proposicoes_lista = []
    if proposicoes and 'dados' in proposicoes:
        ids_proposicoes_lista = [p['id'] for p in proposicoes['dados'] if 'id' in p]
        # Remove duplicatas
        ids_proposicoes_lista = list(dict.fromkeys(ids_proposicoes_lista))

    proposicoes_autores = obter_dados_com_cache_por_id(
        "proposicoes_autores.json",
        base_ids=ids_proposicoes_lista,
        funcao_busca_item=agregar_autores_proposicoes_por_ids,
        checkpoint_intervalo=1000,
        campo_id="idProposicao"
    )

    # 6. Frentes Parlamentares dos Deputados
    deputados_frentes = obter_dados_com_cache_por_id(
        "deputados_frentes.json",
        base_ids=ids_deputados,
        funcao_busca_item=agregar_frentes_deputados_por_ids,
        checkpoint_intervalo=500,
        campo_id="idDeputado"
    )

    # 7. Órgãos dos Deputados
    deputados_orgaos = obter_dados_com_cache_por_id(
        "deputados_orgaos.json",
        base_ids=ids_deputados,
        funcao_busca_item=agregar_orgaos_deputados_por_ids,
        checkpoint_intervalo=500,
        campo_id="idDeputado"
    )

def popular_tabelas():
    console.print(Panel("[bold yellow]→ Populando tabela de deputados...[/bold yellow]", expand=False))
    init_db()
    
    console.print("[bold red]→ Limpando dados antigos do banco...[/bold red]")
    limpar_banco()
    
    console.print("[bold cyan]→ Populando tabela de deputados...[/bold cyan]")
    popular_deputados()
    
    console.print("[bold cyan]→ Populando despesas condensadas por legislatura...[/bold cyan]")
    popular_despesas_legislatura()
    
    console.print("[bold cyan]→ Populando gastos totais condensados por deputado...[/bold cyan]")
    popular_despesas_totais_condensadas()
    
    console.print("[bold cyan]→ Populando despesas mensais por categoria...[/bold cyan]")
    popular_despesas_mensais()
    
    console.print("[bold cyan]→ Calculando e populando estatísticas de gastos...[/bold cyan]")
    popular_estatisticas_gastos()

if __name__ == "__main__":
    executar_processo()
    popular_tabelas()
