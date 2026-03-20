import json
import statistics
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import matplotlib.ticker as ticker

def carregar_id_nomes():
    """
    Carrega o mapeamento de ID para Nome do arquivo deputados.json.
    """
    mapeamento = {}
    try:
        with open('raw/deputados.json', 'r', encoding='utf-8') as f:
            dados = json.load(f)
            for d in dados.get('dados', []):
                mapeamento[str(d['id'])] = d['nome']
    except Exception as e:
        print(f" Aviso: Não foi possível carregar nomes dos deputados: {e}")
    return mapeamento

def plotar_gastos_deputados(dados_despesas, ordenar_por='valor'):
    """
    Gera um gráfico de barras interativo com todos os deputados,
    incluindo um slider para navegar pelo eixo X e linhas de média/DP.
    
    Args:
        dados_despesas: Dados das despesas.
        ordenar_por: 'nome' para alfabética, 'valor' para maior valor (default).
    """
    gastos_por_id = {}
    nomes_mapeados = carregar_id_nomes()
    
    # Agrupamento de gastos por deputado
    if isinstance(dados_despesas, dict) and 'dados' not in dados_despesas:
        for id_dep, conteudo in dados_despesas.items():
            despesas = conteudo.get('dados', []) if isinstance(conteudo, dict) else conteudo
            gastos_por_id[str(id_dep)] = sum(float(d.get('valorLiquido', 0)) for d in despesas if d.get('valorLiquido') is not None)
    else:
        despesas = dados_despesas.get('dados', []) if isinstance(dados_despesas, dict) else dados_despesas
        for d in despesas:
            id_dep = str(d.get('idDeputadoDono') or d.get('id'))
            valor = d.get('valorLiquido', 0)
            if id_dep and valor is not None:
                gastos_por_id[id_dep] = gastos_por_id.get(id_dep, 0) + float(valor)

    if not gastos_por_id:
        print(" Sem dados para plotar.")
        return

    # Preparar todos os dados e nomes
    lista_final = []
    for id_dep, valor in gastos_por_id.items():
        nome = nomes_mapeados.get(id_dep, f"ID {id_dep}")
        lista_final.append((nome, valor))
    
    # Ordenação
    if ordenar_por == 'nome':
        lista_final.sort(key=lambda x: x[0])
    else:
        # Ordenar por MAIOR VALOR
        lista_final.sort(key=lambda x: x[1], reverse=True)
    
    labels = [item[0] for item in lista_final]
    valores = [item[1] for item in lista_final]
    
    # Definição de cores (Ouro, Prata, Bronze para os 3 primeiros)
    cores = []
    for i in range(len(lista_final)):
        if i == 0:
            cores.append('#FFD700')    # Gold
        elif i == 1:
            cores.append('#C0C0C0')    # Silver
        elif i == 2:
            cores.append('#CD7F32')    # Bronze
        else:
            cores.append('skyblue')
    
    # Cálculos estatísticos globais (continuam iguais, pois os valores são os mesmos)
    media = statistics.mean(valores)
    desvio = statistics.stdev(valores) if len(valores) > 1 else 0

    # Configuração da figura e eixos
    fig, ax = plt.subplots(figsize=(15, 8))
    plt.subplots_adjust(bottom=0.25) # Abre espaço para o slider

    # Janela inicial de visualização (ex: primeiros 20 deputados)
    visivel_inicial = 20
    
    # Barras do gráfico com as cores definidas
    barras = ax.bar(labels, valores, alpha=0.8, color=cores, label='Gasto por Deputado')
    
    # Linhas de referência (Média e DP)
    ax.axhline(media, color='red', linestyle='--', label=f'Média: R$ {media:,.2f}')
    ax.axhline(media + desvio, color='orange', linestyle=':', label=f'+1 DP: R$ {(media + desvio):,.2f}')
    ax.axhline(media - desvio, color='orange', linestyle=':', label=f'-1 DP: R$ {(media - desvio):,.2f}')

    ax.set_title(f'Gastos por Deputado (Total: {len(labels)}) - Use o Slider para navegar')
    ax.set_ylabel('Valor Líquido (R$)')
    
    # Formatação do eixo Y com separador de milhar (.)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',').replace(',', '.')))
    
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Configuração inicial do Eixo X
    ax.set_xlim(-0.5, visivel_inicial - 0.5)
    plt.xticks(rotation=45, ha='right', fontsize=9)

    # Criação do Slider
    ax_slider = plt.axes([0.15, 0.1, 0.7, 0.03])
    max_pos = len(labels) - visivel_inicial
    slider = Slider(ax_slider, 'Posição', 0, max_pos, valinit=0, valstep=1)

    def update(val):
        pos = slider.val
        ax.set_xlim(pos - 0.5, pos + visivel_inicial - 0.5)
        fig.canvas.draw_idle()

    slider.on_changed(update)

    print("\n Gráfico interativo iniciado.")
    print(" NOTA: O gráfico interativo requer uma janela de exibição. Se estiver em um terminal remoto, ele pode não abrir.")
    print(" Salvando também a versão estática completa em 'grafico_gastos_completo.png'")
    
    # Salva uma versão bem larga para ver tudo se necessário
    os.makedirs('images', exist_ok=True)
    nome_grafico_estatico = 'images/grafico_gastos_completo.png'
    
    fig_salvar = plt.figure(figsize=(100, 10))
    ax_salvar = fig_salvar.add_subplot(111)
    ax_salvar.bar(labels, valores, color='skyblue')
    ax_salvar.axhline(media, color='red', linestyle='--')
    plt.xticks(rotation=90)
    fig_salvar.savefig(nome_grafico_estatico)
    plt.close(fig_salvar)
    print(f" Versão completa salva em: {nome_grafico_estatico}")

    plt.show()

def plotar_histograma_zscore(dados_despesas, id_legislatura="desconhecida"):
    """
    Gera um histograma dos gastos totais por deputado e sobrepõe
    as zonas de Z-score para identificar anomalias estatísticas.
    Salva a imagem na pasta 'images'.
    """
    gastos_por_id = {}
    
    # Agrupamento de gastos por deputado para o histograma
    if isinstance(dados_despesas, dict) and 'dados' not in dados_despesas:
        for id_dep, conteudo in dados_despesas.items():
            despesas = conteudo.get('dados', []) if isinstance(conteudo, dict) else conteudo
            gastos_por_id[str(id_dep)] = sum(float(d.get('valorLiquido', 0)) for d in despesas if d.get('valorLiquido') is not None)
    else:
        despesas = dados_despesas.get('dados', []) if isinstance(dados_despesas, dict) else dados_despesas
        for d in despesas:
            id_dep = str(d.get('idDeputadoDono') or d.get('id'))
            valor = d.get('valorLiquido', 0)
            if id_dep and valor is not None:
                gastos_por_id[id_dep] = gastos_por_id.get(id_dep, 0) + float(valor)

    if not gastos_por_id:
        print(" Sem dados para o histograma.")
        return

    valores = np.array(list(gastos_por_id.values()))
    media = np.mean(valores)
    desvio = np.std(valores)

    # Configuração do gráfico
    fig, ax = plt.subplots(figsize=(12, 7))
    n, bins, patches = ax.hist(valores, bins=30, color='skyblue', edgecolor='black', alpha=0.7)

    # Linhas de referência Z-score
    ax.axvline(media, color='red', linestyle='solid', linewidth=2, label=f'Média (Z=0): R$ {media:,.2f}')
    
    # Z-scores 1, 2 e 3
    cores_z = ['orange', 'darkorange', 'darkred']
    for i in range(1, 4):
        pos = media + (i * desvio)
        neg = media - (i * desvio)
        ax.axvline(pos, color=cores_z[i-1], linestyle='--', alpha=0.8, label=f'Z={i} (+{i} DP)')
        if neg > 0:
            ax.axvline(neg, color=cores_z[i-1], linestyle='--', alpha=0.3)

    ax.set_title(f'Distribuição de Gastos e Z-Score - Leg. {id_legislatura} (Deteção de Outliers)')
    ax.set_xlabel('Gasto Total do Deputado (R$)')
    ax.set_ylabel('Frequência (Quantidade de Deputados)')
    
    # Formatação do eixo X
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',').replace(',', '.')))
    
    ax.legend()
    ax.grid(axis='y', linestyle=':', alpha=0.6)
    
    # Identificar quantos estão acima de Z=3
    outliers = sum(1 for v in valores if (v - media) / desvio > 3)
    print(f"\n--- Análise de Histograma (Legislatura: {id_legislatura}) ---")
    print(f" Média: R$ {media:,.2f}")
    print(f" Desvio Padrão: R$ {desvio:,.2f}")
    print(f" Outliers Detectados (Z > 3): {outliers} deputado(s)")
    
    # Criar pasta images se não existir
    os.makedirs('images', exist_ok=True)
    
    # Salvar a imagem com nome explicativo
    nome_arquivo = f'images/histograma_deputados_zscore_{id_legislatura}.png'
    fig.savefig(nome_arquivo)
    print(f" Histograma salvo em: {nome_arquivo}")
    
    plt.show()

def calcular_desvio_padrao_gastos(dados_despesas):
    """
    Calcula o desvio padrão dos gastos totais dos deputados.
    """
    gastos_por_id = {}
    
    # Lógica de agrupamento similar à media_por_deputado
    if isinstance(dados_despesas, dict) and 'dados' not in dados_despesas:
        for id_deputado, conteudo in dados_despesas.items():
            despesas = conteudo.get('dados', []) if isinstance(conteudo, dict) else conteudo
            soma = sum(float(d.get('valorLiquido', 0)) for d in despesas if d.get('valorLiquido') is not None)
            gastos_por_id[id_deputado] = soma
    else:
        despesas = dados_despesas.get('dados', []) if isinstance(dados_despesas, dict) else dados_despesas
        for d in despesas:
            id_dep = d.get('idDeputadoDono') or d.get('id')
            valor = d.get('valorLiquido', 0)
            if id_dep and valor is not None:
                gastos_por_id[id_dep] = gastos_por_id.get(id_dep, 0) + float(valor)

    if len(gastos_por_id) < 2:
        print(" Dados insuficientes para calcular o desvio padrão.")
        return 0.0

    valores = list(gastos_por_id.values())
    desvio = statistics.stdev(valores)
    media = statistics.mean(valores)
    
    print(f" Desvio Padrão: R$ {desvio:,.2f}")
    print(f"   Limite Superior (Média + DP): R$ {(media + desvio):,.2f}")
    print(f"   Limite Inferior (Média - DP): R$ {(media - desvio):,.2f}")
    
    return desvio

def calcular_soma_total_valor_liquido(dados_despesas):
    """
    Recebe um dicionário ou lista de despesas e soma todos os valores de 'valorLiquido'.
    """
    soma_total = 0.0
    
    # Se os dados vierem no formato padrão da API {'dados': [...]}
    despesas = dados_despesas.get('dados', []) if isinstance(dados_despesas, dict) else dados_despesas
    
    for despesa in despesas:
        # Garante que o valor existe e é numérico antes de somar
        valor = despesa.get('valorLiquido', 0)
        if valor is not None:
            soma_total += float(valor)
    
    print(f"\n Soma total de valorLiquido: R$ {soma_total:,.2f}")
            
    return soma_total

def gastos_por_tipo(dados_despesas):
    """
    Retorna o total de gastos classificados por tipo de despesa.
    """
    gastos_tipo = {}
    
    # Normalizar a estrutura das despesas para obter uma lista única
    if isinstance(dados_despesas, dict) and 'dados' not in dados_despesas:
        # Se for um dicionário mapeado por ID de deputado {id: {dados: [...]}}
        todas_despesas = []
        for conteudo in dados_despesas.values():
            if isinstance(conteudo, dict) and 'dados' in conteudo:
                todas_despesas.extend(conteudo['dados'])
            elif isinstance(conteudo, list):
                todas_despesas.extend(conteudo)
    else:
        # Se for a lista direta ou dicionário com chave 'dados'
        todas_despesas = dados_despesas.get('dados', []) if isinstance(dados_despesas, dict) else dados_despesas

    for d in todas_despesas:
        tipo = d.get('tipoDespesa', 'Outros')
        valor = d.get('valorLiquido', 0)
        if valor is not None:
            gastos_tipo[tipo] = gastos_tipo.get(tipo, 0.0) + float(valor)
        
    # Ordena pelo maior valor
    gastos_ordenados = dict(sorted(gastos_tipo.items(), key=lambda item: item[1], reverse=True))
    
    print("\n--- Gastos por Tipo de Despesa ---")
    for tipo, total in gastos_ordenados.items():
        print(f" {tipo}: R$ {total:,.2f}")
        
    return gastos_ordenados

def media_por_deputado(dados_despesas):
    """
    Agrupa os valores de valorLiquido por ID do deputado, soma-os e calcula a média geral por deputado.
    """
    gastos_por_id = {}
    
    # Se os dados contiverem dicionários por ID (formato {id: {dados: [...]}})
    if isinstance(dados_despesas, dict) and not 'dados' in dados_despesas:
        for id_deputado, conteudo in dados_despesas.items():
            despesas = conteudo.get('dados', []) if isinstance(conteudo, dict) else conteudo
            soma = sum(float(d.get('valorLiquido', 0)) for d in despesas if d.get('valorLiquido') is not None)
            gastos_por_id[id_deputado] = soma
    else:
        # Se for uma lista única de despesas com campo 'idDeputado'
        despesas = dados_despesas.get('dados', []) if isinstance(dados_despesas, dict) else dados_despesas
        for d in despesas:
            # Tenta pegar idDeputado ou similar dependendo da estrutura
            id_dep = d.get('idDeputadoDono') or d.get('id')
            valor = d.get('valorLiquido', 0)
            if id_dep and valor is not None:
                gastos_por_id[id_dep] = gastos_por_id.get(id_dep, 0) + float(valor)

    if not gastos_por_id:
        return 0.0

    total_gastos = sum(gastos_por_id.values())
    media = total_gastos / len(gastos_por_id)
    
    print(f" Total de deputados analisados: {len(gastos_por_id)}")
    print(f" Média de gastos por deputado: R$ {media:,.2f}")
    
    return media

if __name__ == "__main__":
    try:
        # Tenta carregar dados consolidados por legislatura se existirem, 
        # ou usa o arquivo padrão deputados_despesas.json
        caminho_despesas = 'raw/deputados_despesas.json'
        
        with open(caminho_despesas, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            
            # Agrupar despesas por Legislatura para gerar um Z-Score para cada uma
            despesas_lista = []
            if isinstance(dados, dict):
                despesas_lista = dados.get('dados', [])
            elif isinstance(dados, list):
                despesas_lista = dados

            # Dicionário para separar os dados por ID de Legislatura
            por_legislatura = {}
            for desp in despesas_lista:
                leg_id = str(desp.get('idLegislatura', 'geral'))
                if leg_id not in por_legislatura:
                    por_legislatura[leg_id] = []
                por_legislatura[leg_id].append(desp)

            print(f"\n--- Relatório Estatístico de Despesas ---")
            
            # Processar cada legislatura individualmente
            for leg_id, dados_leg in por_legislatura.items():
                print(f"\n>>> Processando Legislatura: {leg_id}")
                # Criamos um dicionário no formato que as funções esperam
                contexto_leg = {'dados': dados_leg}
                
                calcular_soma_total_valor_liquido(contexto_leg)
                media_por_deputado(contexto_leg)
                plotar_histograma_zscore(contexto_leg, id_legislatura=leg_id)
            
            # Plotar o gráfico de barras interativo (geral ou você pode mover para o loop)
            plotar_gastos_deputados(dados)
            
    except FileNotFoundError:
        print(f" Arquivo '{caminho_despesas}' não encontrado.")
    except Exception as e:
        print(f" Erro ao processar arquivo: {e}")


