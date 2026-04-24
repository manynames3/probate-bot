from __future__ import annotations

from abc import ABC, abstractmethod

from probate_bot.models import ProbateLead, SearchRequest


class BaseScraper(ABC):
    @abstractmethod
    def run(self, request: SearchRequest) -> list[ProbateLead]:
        raise NotImplementedError
