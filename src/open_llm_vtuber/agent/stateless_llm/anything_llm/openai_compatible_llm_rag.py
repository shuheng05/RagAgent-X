"""Description: This file contains the implementation of the `AsyncLLM` class.
This class is responsible for handling asynchronous interaction with OpenAI API compatible
endpoints for language generation.
"""

from typing import AsyncIterator, List, Dict, Any
from openai import (
    AsyncStream,
    AsyncOpenAI,
    APIError,
    APIConnectionError,
    RateLimitError,
)
from openai.types.chat import ChatCompletionChunk
from loguru import logger

from src.open_llm_vtuber.agent.stateless_llm.anything_llm.anything_llm import AnythingLLMConfig
from src.open_llm_vtuber.agent.stateless_llm.stateless_llm_interface import StatelessLLMInterface
import aiohttp
import json


class AsyncLLM(StatelessLLMInterface):
    def __init__(
            self,
            model: str,
            base_url: str,
            llm_api_key: str = "z",
            organization_id: str = "z",
            project_id: str = "z",
            temperature: float = 1.0,
    ):
        """
        Initializes an instance of the `AsyncLLM` class.

        Parameters:
        - model (str): The model to be used for language generation.
        - base_url (str): The base URL for the OpenAI API.
        - organization_id (str, optional): The organization ID for the OpenAI API. Defaults to "z".
        - project_id (str, optional): The project ID for the OpenAI API. Defaults to "z".
        - llm_api_key (str, optional): The API key for the OpenAI API. Defaults to "z".
        - temperature (float, optional): What sampling temperature to use, between 0 and 2. Defaults to 1.0.
        """
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.client = AsyncOpenAI(
            base_url=base_url,
            organization=organization_id,
            project=project_id,
            api_key=llm_api_key,
        )
        self.anything_llm_config = AnythingLLMConfig()

        logger.info(
            f"Initialized AsyncLLM with the parameters: {self.base_url}, {self.model}"
        )

    async def chat_completion(
            self, messages: List[Dict[str, Any]], system: str = None
    ) -> AsyncIterator[str]:
        """
        Generates a chat completion using the OpenAI API asynchronously via HTTP.

        Parameters:
        - messages (List[Dict[str, Any]]): The list of messages to send to the API.
        - system (str, optional): System prompt to use for this completion.

        Yields:
        - str: The content of each chunk from the API response.

        Raises:
        - APIConnectionError: When the server cannot be reached
        - RateLimitError: When a 429 status code is received
        - APIError: For other API-related errors
        """
        logger.debug(f"Messages: {messages}")

        # If system prompt is provided, add it to the messages
        messages_with_system = messages
        if system:
            messages_with_system = [
                {"role": "system", "content": system},
                *messages,
            ]

        anything_llm_url = self.anything_llm_config.url
        anything_llm_api_key = self.anything_llm_config.api_key
        anything_llm_workspace_model = self.anything_llm_config.workspace_model

        headers = {
            "accept": "*/*",
            "Authorization": f"Bearer {anything_llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "messages": messages_with_system,
            "model": anything_llm_workspace_model,
            "stream": True,
            "temperature": self.temperature,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        url=anything_llm_url,
                        headers=headers,
                        json=payload,
                ) as response:
                    if response.status != 200:
                        error_msg = f"API request failed with status {response.status}"
                        logger.error(error_msg)
                        yield f"Error: {error_msg}"
                        return

                    buffer = ""
                    async for chunk in response.content:
                        if chunk:
                            buffer += chunk.decode('utf-8')

                            # Process each complete event in the buffer
                            while "\n\n" in buffer:
                                event, buffer = buffer.split("\n\n", 1)
                                if event.startswith("data: "):
                                    event = event[6:]  # Remove "data: " prefix
                                    if event == "[DONE]":
                                        return

                                    try:
                                        data = json.loads(event)
                                        if "choices" in data and data["choices"]:
                                            content = data["choices"][0]["delta"].get("content", "")
                                            yield content
                                    except json.JSONDecodeError as e:
                                        logger.error(f"Error decoding JSON: {e}")
                                        continue

        except aiohttp.ClientConnectionError as e:
            logger.error(
                f"Error calling the chat endpoint: Connection error. Failed to connect to the LLM API. \nCheck the configurations and the reachability of the LLM backend. \nSee the logs for details. \nTroubleshooting with documentation: https://open-llm-vtuber.github.io/docs/faq#%E9%81%87%E5%88%B0-error-calling-the-chat-endpoint-%E9%94%99%E8%AF%AF%E6%80%8E%E4%B9%88%E5%8A%9E \n{e}"
            )
            yield "Error calling the chat endpoint: Connection error. Failed to connect to the LLM API. Check the configurations and the reachability of the LLM backend. See the logs for details. Troubleshooting with documentation: [https://open-llm-vtuber.github.io/docs/faq#%E9%81%87%E5%88%B0-error-calling-the-chat-endpoint-%E9%94%99%E8%AF%AF%E6%80%8E%E4%B9%88%E5%8A%9E]"

        except Exception as e:
            logger.error(f"LLM API: Error occurred: {e}")
            logger.info(f"Base URL: {self.base_url}")
            logger.info(f"Model: {self.model}")
            logger.info(f"Messages: {messages}")
            logger.info(f"temperature: {self.temperature}")
            yield "Error calling the chat endpoint: Error occurred while generating response. See the logs for details."
