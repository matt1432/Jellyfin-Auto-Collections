from abc import ABC
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import pluginlib

from definitions import BasePluginConfig, PluginResult


@pluginlib.Parent("list_scraper")
class ListScraper(ABC):
    @staticmethod
    @pluginlib.abstractmethod
    def get_list(list_id: str, config: BasePluginConfig) -> PluginResult: ...


if TYPE_CHECKING:

    @runtime_checkable
    class ListScraperClass(Protocol):
        @staticmethod
        def get_list(
            list_id: str, config: BasePluginConfig
        ) -> PluginResult: ...
