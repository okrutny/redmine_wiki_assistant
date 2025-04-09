import ast
from typing import Dict, List

from fastapi import APIRouter, Request

from app.codebase_parser import search_functions_with_keywords, extract_and_save_model_data
from app.keywords_extraction import extract_vars_chain, match_question_to_code_chain, o3_mini_llm
from app.utils import send_log_to_slack
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def answer_with_context(question, snippets):
    combined_snippets = "\n\n---\n\n".join([s for s in snippets])

    prompt = f"""
    You are a technical assistant responsible for building an internal knowledge base based on source code.

    Your task is not only to answer the user's question directly, but also to:

    1. Identify all relevant aspects and subtopics that are either explicitly or implicitly present in the question.
    2. Expand the question to include those additional aspects, so the full technical and functional context is covered.
    3. Based on the identified aspects, find and list the code fragments that illustrate how the relevant logic 
    is implemented in the system.
    4. Using the question and the matching code snippets, provide a complete and well-structured answer. 
    Make sure to explain important behaviors, edge cases, and system mechanisms.

    Your goal is to **help the user understand how the system works**, not just provide a literal answer. 
    If the question is missing something — fill in the gaps. 
    If there are exceptions or hidden dependencies — explain them.

    Your response should be structured logically, for example:

    - Key aspects found in the question
    - Expanded version of the question
    - Code snippets with short explanations
    - Comprehensive answer
    
Question:
{question}

Code snippets:
{combined_snippets}

Answer in polish:
"""

    response = o3_mini_llm.invoke(prompt)
    return response.content.strip()


def answer_with_context_and_history(
    messages: List[Dict[str, str]],
    followup_question: str,
    snippets: list
) -> (str, List[Dict[str, str]]):
    combined_snippets = "\n\n---\n\n".join([s for s in snippets])

    if not any("Code snippets:" in m["content"] for m in messages if m["role"] == "user"):
        base_question = messages[0]["content"]
        messages[0]["content"] = f"{base_question}\n\nCode snippets:\n{combined_snippets}"

    messages.append({"role": "user", "content": followup_question})

    response = o3_mini_llm.invoke(messages)

    messages.append({"role": "assistant", "content": response.content.strip()})
    return response.content.strip(), messages


# def generate_combinations(words, max_len=2):
#     combos = set()
#     split_words = []
#
#     for word in words:
#         # Split the word by space, underscore, and dot
#         components = word.replace('_', ' ').replace('.', ' ').split()
#         split_words.extend(components)
#
#     split_words = set(split_words)
#
#     # Only combinations of up to 3 elements
#     for r in range(1, min(len(split_words), max_len) + 1):
#         for perm in itertools.permutations(split_words, r):
#             combos.add('_'.join(perm))       # snake_case
#             combos.add('.'.join(perm))       # dot.notation
#             combos.add(' '.join(perm))       # space
#
#     return sorted(combos)


def run_qa_pipeline(question):
    send_log_to_slack(f"Processing question: {question}")

    model_names, other_names = extract_and_save_model_data()

    send_log_to_slack(f"Extracting optional variables from question: {question}")
    returned_vars = extract_vars_chain.run(question=question).strip()
    variables = ast.literal_eval(returned_vars)

    matching_models = []
    matching_other = []

    if not variables:
        send_log_to_slack("Variables not found")
        matching_models = ast.literal_eval(match_question_to_code_chain.run(codebase=", ".join(model_names),
                                                                            question=question).strip())

        matching_other = ast.literal_eval(match_question_to_code_chain.run(codebase=", ".join(other_names),
                                                                           question=question).strip())
    else:
        send_log_to_slack(f"Found following variables: {', '.join(variables)}")

    matching_names = matching_models + matching_other + variables

    send_log_to_slack(f"Found following fields and methods in codebase: {', '.join(matching_names)}")

    send_log_to_slack(f"Searching for code...")
    results = search_functions_with_keywords(matching_names)
    all_snippets = []
    for entry in results:
        all_snippets.append(entry["snippet"])

    if not all_snippets:
        send_log_to_slack("No matches found.")
    else:
        send_log_to_slack(f"Found {len(results)} matches - generating response")
        final_answer = answer_with_context(question, all_snippets)
        send_log_to_slack(f"Question: {question}")
        send_log_to_slack(f"LLM response: {final_answer}")
        # messages = [
        #     {
        #         "role": "system",
        #         "content": "You are an expert extracting logical conclusions and consequences from previous "
        #                    "LLM responses. Answer in polish."
        #     },
        #     {
        #         "role": "user",
        #         "content": question
        #     },
        #     {
        #         "role": "assistant",
        #         "content": final_answer
        #     }
        # ]

        # while True:
        #
        #     followup_question = input("\n💬 Follow-up (Enter by przerwać): ")
        #     if not followup_question.strip():
        #         print("Kończę sesję.")
        #         break
        #
        #     followup_answer, messages = answer_with_context_and_history(
        #         messages=messages,
        #         followup_question=followup_question,
        #         snippets=all_snippets
        #     )
        #
        #     print("\n🧠 Odpowiedź (follow-up):")
        #     print(followup_answer)


@router.post("/slack/commands/search_codebase")
async def search_text(request: Request):
    form = await request.form()
    payload = dict(form)
    logger.info(f"Received Slack command: {payload}")

    query = payload.get('text')

    if not query:
        return {"error": "Missing 'query' parameter"}

    run_qa_pipeline(query)
