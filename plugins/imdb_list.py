import json
from typing import cast, final

import bs4
import requests

from definitions import BasePluginConfig, JellyfinItem, ListIDItem, PluginResult
from utils.base_plugin import ListScraper


@final
class IMDBList(ListScraper):
    _alias_ = "imdb_list"

    @staticmethod
    def get_list(
        list_id: str | ListIDItem,
        config: BasePluginConfig,
    ) -> PluginResult:
        if not isinstance(list_id, str):
            if "list_id" in list_id:
                list_id = list_id["list_id"]
            else:
                list_id = str(list_id)

        r = requests.get(
            f"https://www.imdb.com/list/{list_id}",
            headers={
                "Accept-Language": "en-US",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
            },
        )
        soup = bs4.BeautifulSoup(r.text, "html.parser")
        list_name = cast(bs4.Tag, soup.find("h1")).text
        description = cast(
            bs4.Tag, soup.find("div", {"class": "list-description"})
        ).text

        ld_json = cast(
            bs4.Tag, soup.find("script", {"type": "application/ld+json"})
        ).text
        ld_json = json.loads(ld_json)
        movies: list[JellyfinItem] = []
        for row in ld_json["itemListElement"]:
            url_parts = row["item"]["url"].split("/")
            url_parts = [p for p in url_parts if p != ""]

            release_year = None
            if config.get("add_release_year", False):
                # Get release_date
                r = requests.get(
                    row["item"]["url"],
                    headers={
                        "Accept-Language": "en-US",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
                    },
                )
                soup = bs4.BeautifulSoup(r.text, "html.parser")
                movie_json = cast(
                    bs4.Tag,
                    soup.find("script", {"type": "application/ld+json"}),
                ).text
                release_year = json.loads(movie_json)["datePublished"].split(
                    "-"
                )[0]

            movies.append(
                {
                    "title": row["item"]["name"],
                    "release_year": release_year,
                    "media_type": row["item"]["@type"],
                    "imdb_id": url_parts[-1],
                }
            )

        return {
            "name": list_name,
            "items": movies,
            "description": description,
        }
