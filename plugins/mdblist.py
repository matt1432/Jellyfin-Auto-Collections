from typing import cast, final

import bs4
import requests

from definitions import BasePluginConfig, JellyfinItem, PluginResult
from utils.base_plugin import ListScraper


@final
class MDBList(ListScraper):
    _alias_ = "mdblist"

    @staticmethod
    def get_list(list_id: str, config: BasePluginConfig) -> PluginResult:  # pyright: ignore[reportUnusedParameter]
        list_id = list_id.strip("/")

        # Get the list name
        r = requests.get(f"https://mdblist.com/lists/{list_id}")
        soup = bs4.BeautifulSoup(r.text, "html.parser")
        list_name = cast(
            bs4.Tag, soup.select_one("div.ui.form h3")
        ).text.strip()
        description = soup.select("div.ui.form div.fourteen.wide.field p")
        description = "\n".join([p.text for p in description])

        # Get the list items
        r = requests.get(f"https://mdblist.com/lists/{list_id}/json")
        movies = r.json()
        movies = cast(
            list[JellyfinItem],
            [{**movie, "media_type": movie["mediatype"]} for movie in movies],
        )

        return {"name": list_name, "items": movies, "description": description}
