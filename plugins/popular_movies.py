from typing import final

import requests

from definitions import BasePluginConfig, JellyfinItem, ListIDItem, PluginResult
from utils.base_plugin import ListScraper


@final
class PopularMovies(ListScraper):
    """Movies from stevenlu's nightly list"""

    _alias_ = "popular_movies"

    @staticmethod
    def _is_valid_list_id(list_id: str):
        if list_id in [
            "movies",
            "all-movies",
            "movies-metacritic-min50",
            "movies-metacritic-min60",
            "movies-metacritic-min70",
            "movies-metacritic-min80",
            "movies-imdb-min5",
            "movies-imdb-min6",
            "movies-imdb-min7",
            "movies-imdb-min8",
            "movies-rottentomatoes-min50",
            "movies-rottentomatoes-min60",
            "movies-rottentomatoes-min70",
            "movies-rottentomatoes-min80",
        ]:
            return True

        if list_id.startswith("movies-"):
            return True
        return False

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

        if not PopularMovies._is_valid_list_id(list_id):
            raise Exception(f'Invalid list_id "{list_id}" for popular-movies')

        # Get the list name
        r = requests.get(
            f"https://popular-movies-data.stevenlu.com/{list_id}.json"
        )
        items: list[JellyfinItem] = []
        for item in r.json():
            items.append(
                {
                    "title": item["title"],
                    "release_year": None,
                    "imdb_id": item["imdb_id"],
                    "media_type": "movie",
                }
            )

        description = """Popular Movies uses LLMs to evaluate the popularity of movies that are released and are less than 4 months old. Popular Movies considers a multitude of data points such as ratings, popularity, production companies, actors, and more."""

        return {
            "name": "Popular Movies",
            "items": items,
            "description": description,
        }
