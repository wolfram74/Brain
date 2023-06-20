# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
import numpy as np

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import utils
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.docstore.document import Document

from Brain.src.common.brain_exception import BrainException
from Brain.src.common.utils import (
    OPENAI_API_KEY,
    COMMAND_SMS_INDEXS,
    COMMAND_BROWSER_OPEN,
    DEFAULT_GPT_MODEL,
)
from Brain.src.model.req_model import ReqModel
from Brain.src.model.requests.request_model import BasicReq
from Brain.src.rising_plugin.image_embedding import (
    query_image_text,
)

from nemoguardrails.actions import action

from Brain.src.rising_plugin.llm.falcon_llm import FalconLLM
from Brain.src.rising_plugin.llm.gpt_llm import GptLLM
from Brain.src.rising_plugin.llm.llms import (
    get_llm_chain,
    GPT_3_5_TURBO,
    GPT_4_32K,
    GPT_4,
    FALCON_7B,
    GPT_LLM_MODELS,
)

"""
query is json string with below format
{
    "query": string,
    "model": string,
    "uuid": string,
    "image_search": bool,
    "setting": {
        "host_name": string,
        "openai_key": string, 
        "pinecone_key": string, 
        "pinecone_env": string,
        "firebase_key": string,
        "firebase_env": string 
        "settings": {
                "temperature": float
            }, 
        "token": string, 
        "uuid": string, 
    }
}
"""


@action()
async def general_question(query):
    """init falcon model"""
    falcon_llm = FalconLLM()
    """step 0: convert string to json"""
    try:
        json_query = json.loads(query)
    except Exception as ex:
        raise BrainException(BrainException.JSON_PARSING_ISSUE_MSG)
    """step 0-->: parsing parms from the json query"""
    query = json_query["query"]
    model = json_query["model"]
    uuid = json_query["uuid"]
    image_search = json_query["image_search"]
    setting = ReqModel(json_query["setting"])

    """step 1: handle with gpt-4"""
    file_path = os.path.dirname(os.path.abspath(__file__))

    with open(f"{file_path}/phone.json", "r") as infile:
        data = json.load(infile)
    embeddings = OpenAIEmbeddings(openai_api_key=setting.openai_key)

    query_result = embeddings.embed_query(query)
    doc_list = utils.maximal_marginal_relevance(np.array(query_result), data, k=1)
    loader = CSVLoader(file_path=f"{file_path}/phone.csv", encoding="utf8")
    csv_text = loader.load()

    docs = []

    for res in doc_list:
        docs.append(
            Document(
                page_content=csv_text[res].page_content, metadata=csv_text[res].metadata
            )
        )

    """ 1. calling gpt model to categorize for all message"""
    if model in GPT_LLM_MODELS:
        chain_data = get_llm_chain(model=model, setting=setting).run(
            input_documents=docs, question=query
        )
    else:
        chain_data = get_llm_chain(model=DEFAULT_GPT_MODEL, setting=setting).run(
            input_documents=docs, question=query
        )
    try:
        result = json.loads(chain_data)
        # check image query with only its text
        if result["program"] == "image":
            if image_search:
                result["content"] = {
                    "image_name": query_image_text(result["content"], "", uuid)
                }
        """ 2. check program is message to handle it with falcon llm """
        if result["program"] == "message":
            if model == FALCON_7B:
                result["content"] = falcon_llm.query(question=query)
        return str(result)
    except ValueError as e:
        # Check sms and browser query
        if doc_list[0] in COMMAND_SMS_INDEXS:
            return str({"program": "sms", "content": chain_data})
        elif doc_list[0] in COMMAND_BROWSER_OPEN:
            return str({"program": "browser", "content": "https://google.com"})

        return str({"program": "message", "content": falcon_llm.query(question=query)})
