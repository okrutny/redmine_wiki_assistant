from typing import Dict, Any

from langchain.chains.llm import LLMChain
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import PromptTemplate


class ChatOpenAIWithoutTemperature(ChatOpenAI):

    @property
    def _default_params(self) -> Dict[str, Any]:
        """Get the default parameters for calling OpenAI API."""
        params = super()._default_params
        params.pop("temperature", None)  # model o3 does not support temperature
        return params


o3_mini_llm = ChatOpenAIWithoutTemperature(
    model="o3-mini-2025-01-31",
)
#
# gpt4_llm = ChatOpenAI(
#     model="gpt-4",
# )

match_question_to_code_prompt = PromptTemplate.from_template("""
You are a new python programmer, who is tasked in answering the following question:
Question:
{question}

You have to look through a codebase and find relevant models, fields and methods which might be related to the question.

Return all names which seem relevant to the question as a python list of strings, without any additional comments.

Codebase models fields and methods:
{codebase}
""")

match_question_to_code_chain = LLMChain(llm=o3_mini_llm, prompt=match_question_to_code_prompt)


# === Step 0: Extract provided code variables or definitions ===
extract_vars_prompt = PromptTemplate.from_template("""
Given the following question, extract the provided code variables or definitions. 
Every string which contains . or _ is a variable.
 Return them as a python list of strings.
If variables are not provided, return an empty list.    

Question:
{question}
""")

extract_vars_chain = LLMChain(llm=o3_mini_llm, prompt=extract_vars_prompt)

exclude_generic_words_prompt = PromptTemplate.from_template("""
From provided list of nouns, exclude all generic words. By generic i mean words which might have to be too common when
searching for them in python codebase. Return those not generic as flat python list of strings.
Concepts:
{concepts}
""")

exclude_generic_words_chain = LLMChain(llm=o3_mini_llm, prompt=exclude_generic_words_prompt)

exclude_irrelevant_nouns_prompt = PromptTemplate.from_template("""
From provided list of nouns, choose those relevant to the question. Return those as flat python list of strings.
Nouns:
{nouns}

Question:
{question}
""")

exclude_irrelevant_nouns_chain = LLMChain(llm=o3_mini_llm, prompt=exclude_irrelevant_nouns_prompt)

nouns_prompt = PromptTemplate.from_template("""
You are an English native speaker.

from provided list of concepts, find all nouns. Return them as a flat python list of strings.
Concepts:
{concepts}
""")

nouns_chain = LLMChain(llm=o3_mini_llm, prompt=nouns_prompt)

synonyms_prompt = PromptTemplate.from_template("""
You are a python programmer.

Find two synonyms for each noun, which could be used to name function or variable. Return them as a flat python list of strings.

Concepts:
{concepts}
""")

synonyms_chain = LLMChain(llm=o3_mini_llm, prompt=synonyms_prompt)

# === Step 1: Identify concepts ===
concept_prompt = PromptTemplate.from_template("""
You are a Python code assistant.

Identify the main concepts and entities mentioned in the following question.
Make them in a form without any declination and in singular form. Translate them to English. 
Return only english terms, all together in single python list.

Question:
{question}
""")

concept_chain = LLMChain(llm=o3_mini_llm, prompt=concept_prompt)

# === Step 2: Translate to English/synonyms ===
translate_prompt = PromptTemplate.from_template("""
Given the following list of concepts, translate them into English. Return them as a python list of strings. 

Concepts:
{concepts}
""")

translate_chain = LLMChain(llm=o3_mini_llm, prompt=translate_prompt)

# === Step 3.5: Mix terms together ===
mix_terms_prompt = PromptTemplate.from_template("""
create variations of the following terms, using different variations of the same term, 
to generate possible variables names and functions names. Join words with underscore. Return them as a python list of strings.

Terms:
{terms}
""")

mix_terms_chain = LLMChain(llm=o3_mini_llm, prompt=mix_terms_prompt)

# === Step 3: Generate snake_case terms ===
snake_case_prompt = PromptTemplate.from_template("""
Convert the following English terms into possible Python-style variable names using snake_case. Return them as python list

Terms:
{terms}
""")

snake_case_chain = LLMChain(llm=o3_mini_llm, prompt=snake_case_prompt)

# === Step 4: Generate dot.notation terms ===
dot_notation_prompt = PromptTemplate.from_template("""
Convert the following terms into Python-style object.attribute references (dot notation), if applicable. Return them as python list

Terms:
{terms}
""")

dot_notation_chain = LLMChain(llm=o3_mini_llm, prompt=dot_notation_prompt)

# === Step 5: Suggest realistic code names ===
code_name_prompt = PromptTemplate.from_template("""
Based on the provided domain terms and structures, suggest realistic and meaningful Python-style code names for functions, variables, or classes. Focus on terms relevant to business/domain logic.
return them as python list, without any headers, without any parentheses.

Input:
{terms}
""")

code_name_chain = LLMChain(llm=o3_mini_llm, prompt=code_name_prompt)
