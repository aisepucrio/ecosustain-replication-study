# EcoSustain Replication Study

Este repositório contém o estudo de replicação do EcoSustain, permitindo rodar e medir emissões de carbono e uso de recursos do sistema em artefatos Python.

## Estrutura do Repositório

- `scrapping-icse/`: contém o script `scrapping_icse.py`, que gera um CSV com os arquivos ICSE e se possuem artefato ou não.
- `run-dpy/`: scripts para rodar os artefatos com DPY.
- `implement-tools-into-artifact/`: scripts para instrumentar os artefatos com CodeCarbon e psutil.
- `artefatos/`: pasta onde você deve colocar todos os artefatos baixados ou clonados.

## Passo a Passo para Replicação

### 1. Gerar CSV dos Artefatos ICSE

Dentro da pasta `scrapping-icse`:

python scrapping_icse.py


Isso criará um CSV indicando todos os arquivos ICSE e se possuem artefato.

### 2. Organizar os Artefatos

Coloque todos os artefatos baixados ou clonados em uma pasta no seu computador.  
Ex.: `~/EcoSustain/artefatos/`.

### 3. Configurar DPY

Baixe o DPY no seu computador.  

Entre na pasta `run-dpy` e configure:

- `diretorio_dpy` → caminho para o DPY  
- `pasta_base` → caminho para a pasta com os artefatos  
- `pasta_saida_base` → pasta de saída para resultados

### 4. Instrumentar Artefatos com CodeCarbon e Psutil

Abra `implement-tools-into-artifact/implement-tools.py`.  

Altere a variável `artifacts_path` para o caminho da pasta com os artefatos.  

Execute o script:

python implement-tools.py


Isso vai adicionar CodeCarbon e psutil a todos os arquivos `.py` dentro de cada artefato.

### 5. Rodar os Artefatos

Execute qualquer arquivo `.py` dentro de um artefato.  

**IMPORTANTE:** Toda execução cria dois arquivos na pasta do artefato:

- `emissions.csv` → saída do CodeCarbon  
- `psutil_data.csv` → saída do Psutil

⚠️ Renomeie esses arquivos imediatamente após cada execução para evitar sobrescrita ou mistura com outros artefatos.

### 6. Refatorando Artefatos

Nesta etapa, o projeto utiliza uma **pipeline automatizada** que:

1. executa o **DPy** sobre o artefato original;
2. filtra automaticamente apenas *Long Method* (ou outro smell desejado);
3. gera *prompts de refatoração* completos e seguros;
4. refatora o código utilizando **Gemini** ou **OpenAI**;
5. salva as versões refatoradas preservando toda a estrutura do projeto;
6. executa novamente o DPy para avaliar o impacto das refatorações.

---

#### 🛠️ Configuração

Abra o arquivo `main.py` dentro da pasta `refactoring` e configure no topo do script:

# 👉 Nome da pasta do artefato a ser analisado
NOME_ARTEFATO = "Discover-Data-Quality-With-RIOLU"

# Pasta onde estão os artefatos (projetos alvo para refatoração)
PASTA_ARTEFATOS = r"C:\Users\PUC\Documents\AISE\ecosustain-replication-study\artefatos"

# 👉 Tipo de smell a ser filtrado
SMELL_ALVO = "Long method"

# 👉 Caminho da ferramenta DPy instalada no seu PC
DIRETORIO_DPY = r"C:\Users\PUC\Documents\DPy"

# 👉 Diretórios de trabalho na estrutura do projeto
BASE_REFACTOR = r"C:\Users\PUC\Documents\AISE\ecosustain-replication-study\refactoring"
PASTA_OUTPUT_DPY = os.path.join(BASE_REFACTOR, "output-dpy")
PASTA_SAIDA_IA = os.path.join(BASE_REFACTOR, "saida_gemini")
PASTA_FILTERED = os.path.join(BASE_REFACTOR, "filtered-dpy")

Crie um .env para carregar as chaves GEMINI_API_KEY

Depois basta rodar python main.py

| Etapa | Ação                                                              |
| ----- | ----------------------------------------------------------------- |
| 1     | Limpa diretórios de execução anterior                             |
| 2     | Executa o DPy sobre o artefato                                    |
| 3     | Filtra apenas *Long Method* (ou outro smell configurado)          |
| 4     | Gera prompt com trechos reais do smell detectado                  |
| 5     | Refatora utilizando LLM
| 6     | Salva o código   |
| 7     | Executa novamente o DPy para medir o impacto da refatoração       |

Em data_analysis.py:
Configure:
artefato = "Web-Ads-Accessibility"
base_path = r"C:\Users\PUC\Documents\AISE\ecosustain-replication-study\refactoring\output-dpy"

Depois rode python data_analysis.py para ver a comparação dos resultados