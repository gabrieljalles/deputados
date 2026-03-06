from analise_estatistica import (
    calcular_desvio_padrao_gastos, 
    calcular_soma_total_valor_liquido, 
    media_por_deputado,
    plotar_gastos_deputados,
    gastos_por_tipo
)
from api_service import (
    buscar_todas_legislaturas_consolidado,
    buscar_tipos_eventos
)
from parametros import EVENTOS_NAO_OBRIGATORIOS, EVENTOS_OBRIGATORIOS
from file_handler import obter_dados_com_cache_por_arquivo, salvar_em_json
from services import (
    agregar_deputados_por_legislaturas, 
    agregar_detalhes_deputados,
    agregar_despesas_deputados,
    agregar_eventos_por_legislaturas,
    agregar_detalhes_eventos
)
import os
import json

# Parametros ----------------------------
limite_legislaturas = 4 # Define quantas legislaturas a partir da última deve ser baixado.





# ---------------------------------------




def executar_processo():
    print("Iniciando processo de coleta de dados...")
    
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
        eventos_obrigatorios=EVENTOS_OBRIGATORIOS, 
        eventos_nao_obrigatorios=EVENTOS_NAO_OBRIGATORIOS
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

    # 5. Detalhes dos Eventos
    eventos_detalhados = obter_dados_com_cache_por_arquivo(
        "eventos_detalhados.json",
        agregar_detalhes_eventos,
        dados_eventos=eventos
    )

    # 6. Estatísticas e Análises (Estudo por legislatura ou geral)
    soma_total = calcular_soma_total_valor_liquido(deputados_despesas)
    media_deputado = media_por_deputado(deputados_despesas)
    desvio_padrao = calcular_desvio_padrao_gastos(deputados_despesas)
    gastos_tipo = gastos_por_tipo(deputados_despesas)
    
    # 7. Mostrar gráfico
    print("\nComo deseja ordenar o gráfico?")
    print("1 - Por maior valor de gasto (Padrão)")
    print("2 - Por ordem alfabética (Nome)")
    
    opcao = input("Escolha (1 ou 2): ").strip()
    ordem = 'nome' if opcao == '2' else 'valor'
    
    print(f"\nGerando gráfico interativo (ordenado por {ordem})...")
    plotar_gastos_deputados(deputados_despesas, ordenar_por=ordem)

    print(f"\n Processo de coleta concluído com sucesso!")

if __name__ == "__main__":
    executar_processo()
