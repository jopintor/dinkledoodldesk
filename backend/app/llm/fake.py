"""Deterministic offline provider for tests, CI and running the RAG pipeline without a key.

`HashEmbeddings` is a hashed bag of words and bigrams: texts that share words get a high
cosine similarity, which is enough to exercise retrieval end to end, but it is not a
semantic model. Never compare its hit rates with Gemini's.

`FakeChatModel` answers from the first `<context>` source with a `[1]` citation, or
returns `NO_ANSWER` when the prompt has no context. Tests can script replies instead.
"""

import hashlib
import math
import re

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.config import Settings
from app.llm.base import LLMProvider

_WORD = re.compile(r"[a-z0-9]+")
_SOURCE = re.compile(r"^\[1\] .*\n(?P<body>(?:.+\n?)+)", re.MULTILINE)


class HashEmbeddings(Embeddings):
    def __init__(self, dim: int = 768) -> None:
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        words = _WORD.findall(text.lower())
        features = words + [f"{a} {b}" for a, b in zip(words, words[1:], strict=False)]
        vec = [0.0] * self.dim
        for feature in features:
            digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self.dim
            vec[index] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class FakeChatModel(BaseChatModel):
    model_name: str = "fake-chat"
    responses: list[str] = []
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        self.calls += 1
        if self.responses:
            text = self.responses.pop(0)
        else:
            prompt = str(messages[-1].content)
            match = _SOURCE.search(prompt)
            if match is None:
                text = "NO_ANSWER"
            else:
                first_line = match.group("body").strip().splitlines()[0]
                text = f"{first_line.strip()} [1]"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_configured(self) -> bool:
        return True

    def chat_model_name(self, *, fallback: bool = False) -> str:
        return "fake-chat"

    def chat_model(self, *, fallback: bool = False):
        return FakeChatModel()

    def embedding_model_name(self) -> str:
        return "fake-hash"

    def embeddings(self):
        return HashEmbeddings(self._settings.embedding_dim)
