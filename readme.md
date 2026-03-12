# Presença em eventos

[ ] Saber a porcentagem de eventos obrigatórios em que o deputado federal compareceu.

- [ ] Saber a quantidade total de eventos obrigatórios (1)
- [ ] Saber a quantidade total de eventos não obrigatórios (2)
- [ ] Eventos não catalogados e não pontuados (0).

# Discursos realizados

# Votações realizadas e a qualidade das votações.

[ ] Existe a orientação do partido e o que o deputaod do partido realmente vota.

- Se orientação = S e votação = S - Fiel |
- Se orientação = S e votação = N - Infiel |
- Se orientação = N e votação = S - Infiel |
- Se orientação = N e votação = N - Fiel |
- Depois, ver a porcentagem de fidelidade em relação ao total dos dados. - Resultado : Joaquim tem 80% de fidelidade ao partido.

# Gastos e custos do deputado federal

[ ] Saber o quanto cada deputado gasta em realação aos demais no campo geral e no campo específico.
[ ] Saber o quanto cada um gasta comparado a ele mesmo.
[ ] Saber o quanto cada um gasta comparado aos outros no mês.

# Cargos e assessores

[ ] Saber quantos assessores o deputado tem
[ ] Salário médio dos assessores
[ ] Gasto total com assessores
[ ] Comparar com os demais deputados

# Criar troféus mensais / 3 meses

- São distribuídos todos os meses, todo mês recemeça a contagem.
  - (Não sei se vou adaptar para três meses ao invés de um)
- Deputado que mais economizou naquele mês.
- Deputado que mais fez discursos naquele mês.

# Criar selos quantitativos (Produtividade)

- Selos são atividades quantitativas:
  - Selos em que o deputado atinge uma quantidade específica de discursos na Camara.
  - Selos em que o deputado destina X de emendas.
  - Selos em que o deputado Economiza Tanto nos gastos baseado com seus pares.

# Selos de decisão (Postura)

- Selos que mostram que o deputado tomou um lado específico em um momento muito importante.
  - Pec da blindagem
  - Pec da segurança pública
  - Aumento de salário dos deputados.

# Selos de autoria

- Selos de criação de uma lei/ pec importante. Qual o critério? Se repercutiu muito na mídia.

# ---------------------------

[X]Preciso criar um documento de pontuação e explicar o pontuação de cada presença em um evento. (Parametros.py)

# --------------------------

[ ] Criar selo da pec da blindagem positivo / negativo
[ ] Criar selo da lei de aumento do salário generico positivo e negativo.
[ ] Criar selo da pec da segurança pública.

---

# 🗄️ Informações estatísticas para se atentar

Existem deputados que moram mais distantes do que outros. Preciso me atentar ao estado de cada deputado.

# 🗄️ Estrutura do Banco de Dados (SQLite)

O projeto utiliza um banco de dados SQLite (`backend/data/deputados.db`) para armazenar e processar os dados coletados da API da Câmara. Abaixo estão as tabelas principais:

### 1. `deputados`

Armazena as informações básicas e de identificação de cada parlamentar.

- **Campos:** `id` (Texto), `nome`, `siglaPartido`, `siglaUf`, `idLegislatura` (Texto), `urlFoto`, `email`.

### 2. `deputados_despesas_legislatura`

Dados de gastos detalhados por categoria (tipo de despesa) para cada deputado na legislatura.

- **Campos:** `idLegislatura`, `idDeputado`, `tipoDespesa`, `somaValorLiquido`, `rankGastador` (Ranking de quem mais gastou na categoria), `rankEconomizador` (Ranking de quem menos gastou na categoria).

### 3. `deputados_despesas_legislatura_condensado`

Visão consolidada do gasto total de cada deputado, somando todas as categorias.

- **Campos:** `idLegislatura`, `idDeputado`, `valorTotal` (Soma de todas as despesas), `rankGastador` (Ranking geral de gastos), `rankEconomizador` (Ranking geral de economia).

### 4. `estatisticas_gastos`

Armazena cálculos estatísticos calculados sobre os gastos dos deputados para fins de comparação.

- **Tipos de Estudo:**
  - `MS`: Média Simples dos gastos por categoria.
  - `DP`: Desvio Padrão dos gastos por categoria.
- **Objetivo:** Identificar comportamentos atípicos e automatizar a criação de selos de economia.

### 5. `despesas`

Tabela técnica de apoio para registros brutos individuais de despesas (em expansão).

- **Campos:** `id_despesa`, `id_deputado`, `tipo_despesa`, `valor_liquido`, etc.
