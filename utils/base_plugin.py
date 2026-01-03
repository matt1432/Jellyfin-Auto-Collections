import pluginlib

from definitions import BasePluginConfig, ListIDItem, PluginResult


@pluginlib.Parent("list_scraper")
class ListScraper:
    @staticmethod
    @pluginlib.abstractmethod
    def get_list(  # pyright: ignore[reportInvalidAbstractMethod]
        list_id: str | ListIDItem,
        config: BasePluginConfig,
    ) -> PluginResult: ...
