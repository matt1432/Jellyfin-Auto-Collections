from abc import ABC

import pluginlib

from definitions import BasePluginConfig, PluginResult


@pluginlib.Parent("list_scraper")
class ListScraper(ABC):
    @staticmethod
    @pluginlib.abstractmethod
    def get_list(list_id: str, config: BasePluginConfig) -> PluginResult: ...
