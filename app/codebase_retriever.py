import ast
from typing import List, Dict

from app.codebase_parser import search_functions_with_keywords, extract_and_save_model_data
from app.keywords_extraction import extract_vars_chain, match_question_to_code_chain, o3_mini_llm

from app.utils import send_log_to_slack


class CodebaseRetriever:

    def __init__(self, question):
        self.question = question

    def run(self):
        send_log_to_slack(f"Processing question: {self.question}")

        model_names, other_names = extract_and_save_model_data()

        send_log_to_slack(f"Extracting optional variables from question: {self.question}")
        returned_vars = extract_vars_chain.run(question=self.question).strip()
        variables = ast.literal_eval(returned_vars)

        matching_models = []
        matching_other = []

        if not variables:
            send_log_to_slack("Variables not found, searching for keywords in database terms")
            matching_models = ast.literal_eval(match_question_to_code_chain.run(codebase=", ".join(model_names),
                                                                                question=self.question).strip())

            matching_other = ast.literal_eval(match_question_to_code_chain.run(codebase=", ".join(other_names),
                                                                               question=self.question).strip())
        else:
            send_log_to_slack(f"Found following variables: {', '.join(variables)}")

        matching_names = matching_models + matching_other + variables

        matching_names = [name.split('.')[1] if '.' in name else name for name in matching_names]

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
            final_answer = self.answer_with_context(all_snippets)
            send_log_to_slack(f"Question: {self.question}")
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

    def answer_with_context(self, snippets):
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
    {self.question}

    Code snippets:
    {combined_snippets}

    Answer in polish:
    """

        response = o3_mini_llm.invoke(prompt)
        return response.content.strip()

    def answer_with_context_and_history(self,
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
