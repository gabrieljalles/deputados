from api_service import (
    buscar_todas_legislaturas_consolidado
)
from file_handler import obter_dados_com_cache, salvar_em_json
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
    legislaturas_consolidado = obter_dados_com_cache(
        "legislaturas_consolidado.json",
        buscar_todas_legislaturas_consolidado,
        formato="json"
    )
    
    # 1. Lista de Deputados por Legislatura (Agregada no services)
    deputados = obter_dados_com_cache(
        "deputados.json",
        agregar_deputados_por_legislaturas,
        legislaturas_consolidado=legislaturas_consolidado,
        limite_legislaturas=5 
    )

    # 2. Detalhes dos Deputados (Agregada no services)
    deputados_detalhes = obter_dados_com_cache(
        "deputados_detalhados.json",
        agregar_detalhes_deputados,
        dados_deputados=deputados
    )
    
    # Extraímos os IDs dos deputados encontrados acima
    ids_deputados = [d['id'] for d in deputados['dados']]
    
    # 3. Despesas dos Deputados (Apenas Legislatura 57)
    deputados_despesas = obter_dados_com_cache(
        "deputados_despesas.json",
        agregar_despesas_deputados,
        lista_ids_deputados=['204536'],
        ids_legislaturas=[57]
    )

    print("Processo de coleta concluído com sucesso!")

if __name__ == "__main__":
    executar_processo()
