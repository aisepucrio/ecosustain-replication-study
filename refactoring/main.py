import os
import subprocess
import json
from dotenv import load_dotenv
from collections import defaultdict
import shutil

# ============================
# 🔧 CONFIGURAÇÕES DO EXPERIMENTO
# ============================

# 👉 Escolha o provedor de IA
IA_PROVIDER = "gemini" 
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

# 👉 Caminho completo do artefato selecionado
ARTEFATO_PATH = os.path.join(PASTA_ARTEFATOS, NOME_ARTEFATO)
# ============================
# 🔐 CHAVES DE API
# ============================

load_dotenv()

if IA_PROVIDER == "gemini":
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

elif IA_PROVIDER == "openai":
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================
# 🧹 FUNÇÕES AUXILIARES
# ============================

def reset_experimento():
    for pasta in [PASTA_FILTERED, PASTA_OUTPUT_DPY, PASTA_SAIDA_IA]:
        if os.path.exists(pasta):
            for item in os.listdir(pasta):
                caminho_item = os.path.join(pasta, item)
                try:
                    if os.path.isfile(caminho_item) or os.path.islink(caminho_item):
                        os.remove(caminho_item)
                    elif os.path.isdir(caminho_item):
                        shutil.rmtree(caminho_item)
                except Exception as e:
                    print(f"Erro ao excluir {caminho_item}: {e}")


def roda_dpy(path):
    print("Iniciando análises com o DPy...")

    comando = [
        ".\\dpy", "analyze",
        "-i", f'"{path}"',
        "-o", f'"{PASTA_OUTPUT_DPY}"'
    ]

    subprocess.run(" ".join(comando), cwd=DIRETORIO_DPY, shell=True)
    print("Todas as análises foram concluídas.")


def filtra_arquivos(pasta):
    return [f for f in os.listdir(pasta) if f.endswith("_implementation_smells.json")]


def filtrar_por_smell(caminho_arquivo, smell_tipo, pasta_saida):
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        data = json.load(f)

    filtrado = [item for item in data if item.get("Smell") == smell_tipo]
    caminho_saida = os.path.join(pasta_saida, os.path.basename(caminho_arquivo))

    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(filtrado, f, indent=4, ensure_ascii=False)


def prompt_instructions(pasta_output, arquivos):
    smell_list, files = [], []

    for arquivo in arquivos:
        json_path = os.path.join(pasta_output, arquivo)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        grouped = defaultdict(list)
        for item in data:
            file_path = item["File"]
            grouped[file_path].append({
                "smell": item.get("Smell", ""),
                "Line": item.get("Line no", ""),
                "description": item.get("Details", "")
            })

        for file_path, file_smells in grouped.items():
            files.append(file_path)

            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()
                lines = file_content.splitlines()

            snippets = []
            for item in file_smells:
                smell_name = item["smell"]
                smell_desc = item["description"]
                smell_lines = item["Line"]

                if "-" in smell_lines:
                    start, end = [int(x.strip()) for x in smell_lines.split("-")]
                else:
                    start = end = int(smell_lines.strip())

                snippet = "\n".join(lines[start-1:end])
                snippets.append(
                    f"- Smell Type: {smell_name}\n"
                    f"- Description: {smell_desc}\n"
                    f"- Snippet of the Smell:\n{snippet}\n\n"
                )

            smell_report = f"## Original Code\n{file_content}\n\n---\n\n## Detected Code Smells\n{''.join(snippets)}"
            smell_list.append(smell_report)

    return files, smell_list


def gera_prompt(smell_list):
    prompts = []
    for smell in smell_list:
        prompt = f"""
            You are an advanced model specialized in **safe Python code refactoring**.

            Your goal is to transform the code into a **cleaner, more maintainable, and more readable version**, while guaranteeing:
            - **identical behavior**
            - **full module compatibility**
            - **zero API breaks**

            ### Detected Code Smells to Fix
            {smell}

            ### ⚠️ API Stability Rules (DO NOT BREAK)
            - Do NOT rename, move or remove public functions, classes, attributes or variables.
            - Do NOT change any function signature.
            - Preserve imports unless definitively unused.
            - If unsure, treat as public.

            ### 📌 Output Rules
            1. Output only the refactored code.
            2. No explanations or comments.
            3. Do not introduce new smells.
        """
        prompts.append(prompt)
    return prompts


def remove_linhas(file):
    with open(file, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    linhas = linhas[1:-1]
    with open(file, "w", encoding="utf-8") as f:
        f.writelines(linhas)


# ============================
# 🚀 EXECUÇÃO DO PIPELINE
# ============================

reset_experimento()
roda_dpy(ARTEFATO_PATH)

filtrar_por_smell(
    rf"{PASTA_OUTPUT_DPY}\{os.path.basename(ARTEFATO_PATH)}_implementation_smells.json",
    SMELL_ALVO,
    PASTA_FILTERED
)

arquivos = filtra_arquivos(PASTA_FILTERED)
files, smell_list = prompt_instructions(PASTA_FILTERED, arquivos)
prompts = gera_prompt(smell_list)

total = len(prompts)
for i, prompt in enumerate(prompts, start=1):
    progresso = int((i / total) * 100)
    print(f"LLM PENSANDO com {IA_PROVIDER.upper()}... ({progresso}%)")

    if IA_PROVIDER == "gemini":
        resposta = genai.GenerativeModel("gemini-2.0-flash-lite").generate_content(prompt)
        output_text = resposta.text

    elif IA_PROVIDER == "openai":
        response = client.responses.create(model="gpt-5-mini", input=prompt)
        output_text = response.output_text

    caminho_original = files[i - 1]
    caminho_relativo = os.path.relpath(caminho_original, start=ARTEFATO_PATH)
    caminho_novo = os.path.join(PASTA_SAIDA_IA, caminho_relativo)
    os.makedirs(os.path.dirname(caminho_novo), exist_ok=True)

    with open(caminho_novo, "w", encoding="utf-8") as f:
        f.write(output_text)
        print(f"Arquivo salvo em: {caminho_novo}")

    remove_linhas(caminho_novo)

roda_dpy(PASTA_SAIDA_IA)
