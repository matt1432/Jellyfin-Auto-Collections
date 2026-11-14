from typing import cast, final

import bs4
import requests

from definitions import BasePluginConfig, JellyfinItem, ListIDItem, PluginResult
from utils.base_plugin import ListScraper


@final
class CriterionChannel(ListScraper):
    _alias_ = "criterion_channel"

    @staticmethod
    def get_list(
        list_id: str | ListIDItem,
        config: BasePluginConfig,  # pyright: ignore[reportUnusedParameter]
    ) -> PluginResult:
        if not isinstance(list_id, str):
            if "list_id" in list_id:
                list_id = list_id["list_id"]
            else:
                list_id = str(list_id)

        r = requests.get(f"https://www.criterionchannel.com/{list_id}")
        soup = bs4.BeautifulSoup(r.text, "html.parser")

        list_name = cast(
            bs4.Tag, soup.find("h1", class_="collection-title")
        ).text.strip()
        description = cast(
            bs4.Tag, soup.find("div", class_="collection-description")
        ).text.strip()

        items: list[JellyfinItem] = []
        for item in soup.find_all("li", class_="js-collection-item"):
            title = cast(bs4.Tag, item.find("strong")).text.strip()
            year_text = cast(bs4.Tag, item.find("p")).text
            if "•" in year_text:
                year_text = year_text.split("•")[1]
            year_text = year_text.strip()
            items.append(
                {
                    "title": title,
                    "release_year": int(year_text)
                    if year_text.isdigit()
                    else None,
                    "media_type": "movie",
                }
            )

        return {
            "name": list_name,
            "items": items,
            "description": description,
        }
