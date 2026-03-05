from analise_estatistica import (
    calcular_desvio_padrao_gastos, 
    calcular_soma_total_valor_liquido, 
    media_por_deputado,
    plotar_gastos_deputados
)
from api_service import (
    buscar_todas_legislaturas_consolidado
)
from file_handler import obter_dados_com_cache_por_arquivo, salvar_em_json
from services import (
    agregar_deputados_por_legislaturas, 
    agregar_detalhes_deputados,
    agregar_despesas_deputados
)
import os
import json

def executar_processo():
    print("Iniciando processo de coleta de dados...")
    
    # 0. Legislaturas Consolidadas
    legislaturas_consolidado = obter_dados_com_cache_por_arquivo(
        "legislaturas_consolidado.json",
        buscar_todas_legislaturas_consolidado,
        formato="json"
    )
    
    # 1. Lista de Deputados por Legislatura (Agregada no services)
    deputados = obter_dados_com_cache_por_arquivo(
        "deputados.json",
        agregar_deputados_por_legislaturas,
        legislaturas_consolidado=legislaturas_consolidado,
        limite_legislaturas=1 
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
    
    # 4. Estatísticas e Análises (Estudo por legislatura ou geral)
    soma_total = calcular_soma_total_valor_liquido(deputados_despesas)
    media_deputado = media_por_deputado(deputados_despesas)
    desvio_padrao = calcular_desvio_padrao_gastos(deputados_despesas)
    
    # 5. Mostrar gráfico
    print("\nGerando gráfico interativo...")
    plotar_gastos_deputados(deputados_despesas)

    print(f"\n Processo de coleta concluído com sucesso!")

if __name__ == "__main__":
    executar_processo()
