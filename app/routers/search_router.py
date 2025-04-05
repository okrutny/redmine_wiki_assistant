import ast
import os
import re
from typing import Dict, Any, List

from fastapi import APIRouter, Request
from langchain.chains.llm import LLMChain
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

router = APIRouter()

WIKI_BASE = os.getenv("REDMINE_WIKI_BASE_URL", "")

# ====== USTAWIENIA ======
CODE_DIR = "/home/okrutny/PycharmProjects/redmine_wiki_assistant/codebase2"  # Ścieżka do folderu z kodem
OPENAI_MODEL = "gpt-4"     # Można też użyć gpt-3.5-turbo
TEMPERATURE = 0            # Dla deterministycznych wyników
CONTEXT_LINES = 5          # Liczba linii przed i po znalezieniu dopasowania

# ====== LANGCHAIN - PARSER I PROMPT ======
response_schemas = [
    ResponseSchema(name="keywords_en", description="Lista przetłumaczonych słów kluczowych po angielsku"),
    ResponseSchema(name="code_names", description="Lista możliwych nazw funkcji, zmiennych lub klas w stylu Pythona")
]
parser = StructuredOutputParser.from_response_schemas(response_schemas)

# prompt = ChatPromptTemplate.from_messages([
#     ("system", "Jesteś doświadczonym inżynierem oprogramowania pracującym z kodem Pythona."),
#     ("user",
#      "Na podstawie pytania użytkownika po polsku wykonaj następujące kroki:\n"
#      "1. Wypisz tylko istotne słowa kluczowe, które odnoszą się do logiki biznesowej, obiektów domenowych "
#      "lub nazwanych bytów (np. 'numer zamówienia', 'identyfikator klienta'). "
#      "Nie wypisuj ogólnych czasowników jak 'generować', 'tworzyć', 'ustawiać'."
#      "Jak dostajesz nazwę zmiennej z kropką traktuj to as-is as a code_name. same with def xyz\n"
#      "2. Przetłumacz te wyrażenia na angielski — również w formie rzeczowników lub nazw domenowych.\n"
#      "3. Na podstawie tych pojęć zaproponuj sensowne i realistyczne nazwy funkcji, zmiennych lub klas w stylu Pythona.\n\n"
#      "Nie twórz nazw generycznych. Skup się na istotnych terminach. Zwróć wynik w formacie JSON zgodnie z tym wzorem:\n"
#      "{format_instructions}\n\n"
#      "Pytanie: {question}"
#     )
# ])
#
# prompt = ChatPromptTemplate.from_messages([
#     ("system", "Jesteś doświadczonym inżynierem oprogramowania pracującym z kodem Pythona."),
#     ("user",
#      "Na podstawie pytania użytkownika po polsku wykonaj następujące kroki:\n"
#      "1. Wypisz tylko istotne słowa kluczowe, które odnoszą się do logiki biznesowej, obiektów domenowych lub nazwanych bytów. "
#      "Unikaj ogólnych czasowników jak 'generować', 'tworzyć', 'ustawiać'.\n"
#      "2. Jeżeli któryś z tych terminów sugeruje związek typu obiekt–pole (np. coś należy do czegoś), przekształć go do reprezentacji kodowej w formacie `obiekt.pole`, zgodnie z dobrymi praktykami kodu Python. "
#      "Zachowaj te formy w polu `code_names`.\n"
#      "3. Przetłumacz każdy z terminów na angielski w możliwie najbliższej formie kodowej (np. w stylu Pythona: snake_case lub dot.notation).\n"
#      "4. Na podstawie tych pojęć zaproponuj realistyczne i sensowne nazwy funkcji, zmiennych lub klas w stylu Pythona. "
#      "Nie twórz nazw zbyt ogólnych — skup się na kontekście domenowym.\n\n"
#       "Zwróć wynik w formacie JSON zgodnie z tym wzorem:\n"
#      "{format_instructions}\n\n"
#      "Pytanie: {question}"
#     )
# ])

# prompt = ChatPromptTemplate.from_messages([
#     ("system", "You are an experienced software engineer working with Python code."),
#     ("user",
#      "Based on the user's question in natural language, perform the following steps:\n"
#      "- identify the main concepts in the question.\n - What the user asks about? Write the answer."
#      "- generate words - direct translation to english or synonyms of what the user asks about.\n"
#      "- Convert words into terms which might be used in python code - different variations of the words connected with underscore"
#      "- Create duplicated list of those terms, but now connect those words making those therms with a dot \n"
#      "- If any of the terms imply an object–attribute relationship (e.g., something belonging to something else), transform it into a code-like `object.attribute` format, following Python best practices. "
#      "Include these forms under the `code_names` field.\n"
#      "- Based on these concepts, suggest realistic and meaningful names for functions, variables, or classes in Python style. "
#      "Avoid overly generic names — focus on domain-relevant context.\n\n"
#      "Return the result in JSON format as per the following schema:\n"
#      "{format_instructions}\n\n"
#      "Question: {question}"
#     )
# ])
#
# llm = ChatOpenAI(model=OPENAI_MODEL, temperature=TEMPERATURE)
#
# chain = prompt | llm | parser

llm = ChatOpenAI(model="gpt-4", temperature=0)

# === Step 0: Extract provided code variables or definitions ===
extract_vars_prompt = PromptTemplate.from_template("""
Given the following question, extract the provided code variables or definitions. Return them as a python list of strings.

Question:
{question}
""")

extract_vars_chain = LLMChain(llm=llm, prompt=extract_vars_prompt)

# === Step 1: Identify concepts ===
concept_prompt = PromptTemplate.from_template("""
You are a Python code assistant.

Identify the main concepts and entities mentioned in the following question. 
Make them in a form without any declination and in singular form. Return them as a python list.

Question:
{question}
""")

concept_chain = LLMChain(llm=llm, prompt=concept_prompt)

# === Step 2: Translate to English/synonyms ===
translate_prompt = PromptTemplate.from_template("""
Given the following list of concepts, translate them into English. Return them as a python list of strings.

Concepts:
{concepts}
""")

translate_chain = LLMChain(llm=llm, prompt=translate_prompt)

# === Step 3.5: Mix terms together ===
mix_terms_prompt = PromptTemplate.from_template("""
create variations of the following terms, using different variations of the same term, 
to generate possible variables names and functions names. Join words with underscore. Return them as a python list of strings.

Terms:
{terms}
""")

mix_terms_chain = LLMChain(llm=llm, prompt=mix_terms_prompt)

# === Step 3: Generate snake_case terms ===
snake_case_prompt = PromptTemplate.from_template("""
Convert the following English terms into possible Python-style variable names using snake_case. Return them as python list

Terms:
{terms}
""")

snake_case_chain = LLMChain(llm=llm, prompt=snake_case_prompt)

# === Step 4: Generate dot.notation terms ===
dot_notation_prompt = PromptTemplate.from_template("""
Convert the following terms into Python-style object.attribute references (dot notation), if applicable. Return them as python list

Terms:
{terms}
""")

dot_notation_chain = LLMChain(llm=llm, prompt=dot_notation_prompt)

# === Step 5: Suggest realistic code names ===
code_name_prompt = PromptTemplate.from_template("""
Based on the provided domain terms and structures, suggest realistic and meaningful Python-style code names for functions, variables, or classes. Focus on terms relevant to business/domain logic.
return them as python list, without any headers, without any parentheses.

Input:
{terms}
""")

code_name_chain = LLMChain(llm=llm, prompt=code_name_prompt)


# ====== PRZESZUKIWANIE KODU ======
def search_codebase(code_names, context_lines=CONTEXT_LINES):
    matches = {}
    patterns = [re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE) for term in code_names]

    for root, _, files in os.walk(CODE_DIR):
        for file in files:
            if file.endswith(".py") or file.endswith(".txt"):
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                except Exception as e:
                    print(f"Nie udało się otworzyć pliku {full_path}: {e}")
                    continue

                for i, line in enumerate(lines):
                    for j, p in enumerate(patterns):
                        if p.search(line):
                            start = max(i - context_lines, 0)
                            end = min(i + context_lines + 1, len(lines))
                            code_snippet = "".join(lines[start:end])
                            if not matches.get(code_names[j]):
                                matches[code_names[j]] = []
                            matches[code_names[j]].append({
                                "file": full_path,
                                "line_number": i + 1,
                                "snippet": code_snippet,
                                "pattern": p
                            })
    return matches


class ChatOpenAIWithoutTemperature(ChatOpenAI):

    @property
    def _default_params(self) -> Dict[str, Any]:
        """Get the default parameters for calling OpenAI API."""
        params = super()._default_params
        params.pop("temperature", None)  # model o3 does not support temperature
        return params

def answer_with_context(question, snippets):
    # Połącz znalezione fragmenty kodu
    combined_snippets = "\n\n---\n\n".join([s for s in snippets])

    # Zbuduj prompt
    prompt = f"""
    You are a technical assistant responsible for building an internal knowledge base based on source code.

    Your task is not only to answer the user's question directly, but also to:

    1. Identify all relevant aspects and subtopics that are either explicitly or implicitly present in the question.
    2. Expand the question to include those additional aspects, so the full technical and functional context is covered.
    3. Based on the identified aspects, find and list the code fragments that illustrate how the relevant logic is implemented in the system.
    4. Using the question and the matching code snippets, provide a complete and well-structured answer. Make sure to explain important behaviors, edge cases, and system mechanisms.

    Your goal is to **help the user understand how the system works**, not just provide a literal answer. If the question is missing something — fill in the gaps. If there are exceptions or hidden dependencies — explain them.

    Your response should be structured logically, for example:

    - Key aspects found in the question
    - Expanded version of the question
    - Code snippets with short explanations
    - Comprehensive answer

Pytanie:
{question}

Fragmenty kodu:
{combined_snippets}

Odpowiedź:
"""

    base_llm = ChatOpenAIWithoutTemperature(
        model="o3-mini-2025-01-31",
    )
    response = base_llm.invoke(prompt)
    return response.content.strip()

def answer_with_context_and_history(
    messages: List[Dict[str, str]],
    followup_question: str,
    snippets: list
) -> (str, List[Dict[str, str]]):
    combined_snippets = "\n\n---\n\n".join([s for s in snippets])

    # Dodaj snippet tylko do pierwszego pytania — jeśli nie ma go jeszcze w historii
    if not any("Fragmenty kodu:" in m["content"] for m in messages if m["role"] == "user"):
        base_question = messages[0]["content"]
        messages[0]["content"] = f"{base_question}\n\nFragmenty kodu:\n{combined_snippets}"

    # Dodaj nowy follow-up
    messages.append({"role": "user", "content": followup_question})

    llm = ChatOpenAIWithoutTemperature(model="o3-mini-2025-01-31")
    response = llm.invoke(messages)

    messages.append({"role": "assistant", "content": response.content.strip()})
    return response.content.strip(), messages

import itertools

import os
import ast

def search_functions_with_keywords(keywords, code_dir=CODE_DIR):
    matches = []

    for root, _, files in os.walk(code_dir):
        for file in files:

            full_path = os.path.join(root, file)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    source = f.read()
            except Exception as e:
                print(f"Cannot read {full_path}: {e}")
                continue

            try:
                tree = ast.parse(source)
            except SyntaxError as e:
                print(f"Cannot parse {full_path}: {e}")
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_start = node.lineno - 1
                    func_end = getattr(node, 'end_lineno', None)

                    if func_end is None:
                        # fallback if Python < 3.8 — use indentation trick
                        func_lines = source.splitlines()[func_start:]
                        for i, line in enumerate(func_lines[1:], 1):
                            if line.strip() and not line.startswith((" ", "\t")):
                                func_end = func_start + i
                                break
                        if func_end is None:
                            func_end = len(source.splitlines())

                    func_body = source.splitlines()[func_start:func_end]
                    func_code = "\n".join(func_body)
                    if any(kw.lower() in func_code.lower() for kw in keywords):
                        matches.append({
                            "file": full_path,
                            "function_name": node.name,
                            "line_number": func_start + 1,
                            "snippet": func_code
                        })

    return matches


def expand_code_names(response: dict) -> list[str]:
    base = set(response.get("code_names", []))
    keywords = response.get("keywords_en", [])

    def normalize(word):
        return word.lower().replace(" ", "_").replace("-", "_")

    normalized = [normalize(w) for w in keywords if w.strip()]

    # Kombinacje par słów
    for w1, w2 in itertools.permutations(normalized, 2):
        base.update([
            f"{w1}_{w2}",
            f"{w2}_{w1}",
            f"{w1}.{w2}",
            f"{w2}.{w1}"
        ])

    # Warianty pojedynczych słów
    for w in normalized:
        base.update([
            w,
            w.replace("_", ""),           # ordernumber
            f"get_{w}",
            f"set_{w}",
            f"{w}_id",
            f"{w}_value",
        ])

    return list(base.union(response.get("code_names", [])))

import itertools

def to_camel(words):
    return words[0].lower() + ''.join(w.capitalize() for w in words[1:])

def generate_combinations(words, max_len=3):
    combos = set()

    # tylko kombinacje 2- i 3-elementowe
    for r in range(2, min(len(words), max_len) + 1):
        for perm in itertools.permutations(words, r):
            combos.add('_'.join(perm))       # snake_case
            combos.add('.'.join(perm))       # dot.notation
            combos.add(' '.join(perm))       # space
            combos.add(to_camel(perm))       # camelCase

    return sorted(combos)

def run_full_keyword_extraction_pipeline(question: str) -> dict:

    concepts = []
    translated = []
    snake_terms = []
    dot_terms = []
    mix_terms = []

    # Step 0
    code_names = ast.literal_eval(extract_vars_chain.run(question=question).strip())

    if not code_names:

        # Step 1
        concepts = concept_chain.run(question).strip()

        # Step 2
        translated = ast.literal_eval(translate_chain.run(concepts=concepts).strip())

        mix_terms = generate_combinations(translated)

        # mix_terms = ast.literal_eval(mix_terms_chain.run(terms=translated).strip())

        # # Step 3
        # snake_terms = ast.literal_eval(snake_case_chain.run(terms=mix_terms).strip())

        # Step 4
        # dot_terms = ast.literal_eval(dot_notation_chain.run(terms=mix_terms).strip())

        # Step 5
        code_names = ast.literal_eval(code_name_chain.run(terms=mix_terms).strip())


    return {
        "concepts": concepts,
        "translated_terms": translated,
        "snake_case_terms": snake_terms,
        "dot_notation_terms": dot_terms,
        "code_names": code_names+mix_terms,
    }

# ====== GŁÓWNA FUNKCJA ======
def run_qa_pipeline(question):
    print(f"\n[1] Przetwarzanie pytania: {question}")

    # formatted_prompt = prompt.format(
    #     question=question,
    #     format_instructions=parser.get_format_instructions()
    # )
    #
    # print(f"\nPrompt:\n{formatted_prompt}")

    # for message in formatted_prompt.to_messages():
    #     print(f"{message.role.upper()}: {message.content}\n")

    # response = chain.invoke({
    #     "question": question,
    #     "format_instructions": parser.get_format_instructions()
    # })

    response = run_full_keyword_extraction_pipeline(question)

    terms = set(response['code_names']+response['dot_notation_terms']+response['snake_case_terms'])
    print("\n[2] Słowa kluczowe i propozycje:")
    print(terms)
    # expanded_code_names = expand_code_names(response)
    # print(f"Expanded code names: {expanded_code_names}")

    print("\n[3] Szukanie kodu...")
    # results = search_codebase(list(terms))
    # for code_name, entries in results.items():
    #     for entry in entries:
    #         all_snippets.append(entry["snippet"])

    results = search_functions_with_keywords(list(terms))
    all_snippets = []
    for entry in results:
        all_snippets.append(entry["snippet"])

    if not all_snippets:
        print("Nie znaleziono żadnych dopasowań.")
    else:
        print(f"\nZnaleziono {len(results)} dopasowań — generuję odpowiedź...\n")
        final_answer = answer_with_context(question, all_snippets)
        print("Pytanie: ", question)
        print("🧠 Odpowiedź LLM:")
        print(final_answer)
        messages = [
            {
                "role": "system",
                "content": "Jesteś analitykiem wyciągającym logiczne wnioski i konsekwencje z poprzednich odpowiedzi innego LLM"
            },
            {
                "role": "user",
                "content": question
            },
            {
                "role": "assistant",
                "content": final_answer
            }
        ]

        while True:

            followup_question = input("\n💬 Follow-up (Enter by przerwać): ")
            if not followup_question.strip():
                print("Kończę sesję.")
                break

            followup_answer, messages = answer_with_context_and_history(
                messages=messages,
                followup_question=followup_question,
                snippets=all_snippets
            )

            print("\n🧠 Odpowiedź (follow-up):")
            print(followup_answer)



@router.post("/search")
async def search_text(request: Request):
    data = await request.json()
    query = data.get("query")

    if not query:
        return {"error": "Missing 'query' parameter"}

    chunks = run_qa_pipeline(query)
    print(chunks)
