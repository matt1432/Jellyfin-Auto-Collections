from typing import final

import requests

from definitions import (
    JellyfinItem,
    JellyfinPluginConfig,
    ListIDItem,
    PluginResult,
)
from utils.base_plugin import ListScraper


@final
class JellyfinAPI(ListScraper):
    """Generate collections based on Jellyfin API queries"""

    _alias_ = "jellyfin_api"

    @staticmethod
    def get_list(
        list_id: ListIDItem, config: JellyfinPluginConfig
    ) -> PluginResult:
        """Call jellyfin API
        list_id should be a dict to pass to https://api.jellyfin.org/#tag/Items/operation/GetItems
        """

        # If list name/desc have been manually specified - grab them
        list_name = f"{list_id}"
        list_desc = f"Movies which match the jellyfin API query: {list_id}"
        if "list_name" in list_id:
            list_name = list_id["list_name"]
            del list_id["list_name"]
        if "list_desc" in list_id:
            list_desc = list_id["list_desc"]
            del list_id["list_desc"]

        params = {
            "enableTotalRecordCount": "false",
            "enableImages": "false",
            "Recursive": "true",
            "fields": ["ProviderIds", "ProductionYear"],
        }
        params = {**params, **list_id}

        res = requests.get(
            f"{config['server_url']}/Users/{config['user_id']}/Items",
            headers={"X-Emby-Token": config["api_key"]},
            params=params,  # pyright: ignore[reportArgumentType]
        )

        items: list[JellyfinItem] = []
        for item in res.json()["Items"]:
            items.append(
                {
                    "title": item["Name"],
                    "release_year": item.get("ProductionYear", None),
                    "media_type": item["Type"],
                    "imdb_id": item["ProviderIds"].get("Imdb", None),
                }
            )

        return {"name": list_name, "description": list_desc, "items": items}
