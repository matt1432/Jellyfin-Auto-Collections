from typing import final

from definitions import (
    BasePluginConfig,
    ListIDItem,
    PluginResult,
)
from utils.base_plugin import ListScraper


@final
class Arr(ListScraper):
    """Generate collections directly from the config file"""

    _alias_ = "local"

    @staticmethod
    def get_list(
        list_id: str | ListIDItem,
        config: BasePluginConfig,  # pyright: ignore[reportUnusedParameter]
    ) -> PluginResult:
        """Call arr API"""
        if isinstance(list_id, str):
            raise TypeError("Local must have objects in list_ids")

        if "list_name" not in list_id:
            raise TypeError("Local must have list_name")

        return {
            "name": list_id["list_name"],
            "description": "",
            # Handled in main.py
            "items": [],
        }
