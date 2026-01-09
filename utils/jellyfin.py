import concurrent.futures
import json
import os
from base64 import b64encode
from typing import TypedDict, cast, final

import requests
from loguru import logger

from definitions import ItemType, JellyfinImageType, JellyfinItem

from .poster_generation import (
    create_mosaic,
    fetch_item_posters,
    get_font,
    safe_download,
)


class Item(TypedDict):
    Id: str
    Name: str
    Tags: list[str]
    Overview: str


class PItem(TypedDict):
    Id: str
    ProviderIds: dict[str, str]
    ProductionYear: int


@final
class JellyfinClient:
    server_url: str
    api_key: str
    user_id: str
    item_type: ItemType = "collection"

    item_type_to_jellyfin_type_map = {
        "collection": "BoxSet",
        "playlist": "Playlist",
    }

    imdb_to_jellyfin_type_map = {
        "movie": ["Movie"],
        "short": ["Movie"],
        "tvEpisode": ["TvProgram", "Episode"],
        "tvSeason": ["Season"],
        "tvSeries": ["Program", "Series"],
        "tvShort": ["TvProgram", "Episode", "Program"],
        "tvMiniSeries": ["Program", "Series"],
        "tvMovie": ["Movie", "TvProgram", "Episode"],
        "video": ["Movie", "TvProgram", "Episode", "Series"],
        "show": ["Program", "Series"],
    }

    def __init__(self, server_url: str, api_key: str, user_id: str):
        self.server_url = server_url
        self.api_key = api_key
        self.user_id = user_id

        # Check if server is reachable
        try:
            _ = requests.get(self.server_url)
        except requests.exceptions.ConnectionError:
            raise Exception("Server is not reachable")

        # Check if api key is valid
        res = requests.get(
            f"{self.server_url}/System/Info",
            headers={"X-Emby-Token": self.api_key},
        )
        if res.status_code != 200:
            raise Exception("Invalid API key")

        jf_info = res.json()
        logger.debug(f"Jellyfin Version: {jf_info['Version']}")

        # Check if user id is valid
        res = requests.get(
            f"{self.server_url}/Users/{self.user_id}",
            headers={"X-Emby-Token": self.api_key},
        )
        if res.status_code != 200:
            raise Exception("Invalid user id")

    def get_items_of_type(self, item_type: ItemType) -> list[Item]:
        params = {
            "enableTotalRecordCount": "false",
            "enableImages": "false",
            "Recursive": "true",
            "includeItemTypes": self.item_type_to_jellyfin_type_map.get(
                item_type, None
            ),
            "fields": ["Name", "Id", "Tags"],
        }
        logger.info(f"Getting {item_type}s list...")
        res = requests.get(
            f"{self.server_url}/Users/{self.user_id}/Items",
            headers={"X-Emby-Token": self.api_key},
            params=params,
        )
        return res.json()["Items"]

    def find_item_with_name_or_create(
        self,
        *,
        item_type: ItemType,
        list_name: str,
        list_id: str,
        description: str | None,
        plugin_name: str,
    ) -> str:
        """Returns the item id of the item with the given name. If it doesn't exist, it creates a new item and returns the id of the new item."""
        self.item_type = item_type

        item_id = None
        items = self.get_items_of_type(self.item_type)

        # Check if list name in tags
        for item in items:
            if json.dumps(list_id) in item["Tags"]:
                item_id = item["Id"]
                break

        # if no match - Check if list name == item name
        if item_id is None:
            for item in items:
                if list_name == item["Name"]:
                    item_id = item["Id"]
                    break

        if item_id is not None:
            logger.info(
                f"found existing {self.item_type}: "
                + list_name
                + " ("
                + item_id
                + ")"
            )

        if item_id is None:
            # item doesn't exist -> Make a new one
            logger.info(
                f"No matching {self.item_type} found for: "
                + list_name
                + f". Creating new {self.item_type}..."
            )
            if self.item_type == "collection":
                res2 = requests.post(
                    f"{self.server_url}/Collections",
                    headers={"X-Emby-Token": self.api_key},
                    params={"name": list_name},
                )
            else:  # if self.item_type == "playlist":
                res2 = requests.post(
                    f"{self.server_url}/Playlists",
                    headers={"X-Emby-Token": self.api_key},
                    json={
                        "Name": list_name,
                        "Ids": [],
                        "UserId": self.user_id,
                        "MediaType": "Video",
                        "Users": [],
                        "IsPublic": True,
                    },
                )
            item_id = res2.json()["Id"]

        # Update item description and add tags so we can find it later
        item = cast(
            Item,
            requests.get(
                f"{self.server_url}/Users/{self.user_id}/Items/{item_id}",
                headers={"X-Emby-Token": self.api_key},
            ).json(),
        )
        if description is not None:
            item["Overview"] = description
        item["Tags"] = list(
            set(
                item.get("Tags", [])
                + [
                    "Jellyfin-Auto-Collections",
                    plugin_name,
                    json.dumps(list_id),
                ]
            )
        )
        item = {
            **item,
            "Name": list_name,
        }
        if self.item_type == "collection":
            item["OriginalTitle"] = list_name
        _ = requests.post(
            f"{self.server_url}/Items/{item_id}",
            headers={"X-Emby-Token": self.api_key},
            json=item,
        )

        return item_id

    def has_poster(self, item_id: str):
        """Check if an item already has a poster"""
        poster_url = f"{self.server_url}/Items/{item_id}/Images/Primary"
        r = requests.get(poster_url, headers={"X-Emby-Token": self.api_key})
        if r.status_code == 404:
            return False
        return True

    def set_poster(
        self,
        *,
        item_id: str,
        item_name: str,
        image_type: JellyfinImageType = JellyfinImageType.PRIMARY,
        url: str,
    ):
        safe_name = item_name.replace(" ", "_").replace("/", "_")
        output_path = f"/tmp/{safe_name}_{image_type}.jpg"

        from PIL import Image

        img = None
        if os.path.exists(url):
            img = Image.open(url)  # or whatever format
            img = img.convert("RGB")  # Ensures it's safe for JPEG
        else:
            img = safe_download(url, {})

        if img is None:
            return

        img.save(output_path, format="JPEG")

        with open(output_path, "rb") as f:
            img_data = f.read()
        encoded_data = b64encode(img_data)

        headers = {
            "X-Emby-Token": self.api_key,
            "Content-Type": "image/jpeg",
        }
        _ = requests.post(
            f"{self.server_url}/Items/{item_id}/Images/{image_type}",
            headers=headers,
            data=encoded_data,
        )

    def make_poster(
        self,
        item_id: str,
        item_name: str,
        mosaic_limit: int = 20,
        google_font_url: str = "https://fonts.googleapis.com/css2?family=Dosis:wght@800&display=swap",
    ):
        # Check if item poster exists
        poster_urls = fetch_item_posters(
            self.server_url, self.api_key, self.user_id, item_id
        )[:mosaic_limit]
        headers = {"X-Emby-Token": self.api_key}

        # Use a ThreadPoolExecutor to download images in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(safe_download, url, headers)
                for url in poster_urls
            ]
            results = [
                future.result()
                for future in concurrent.futures.as_completed(futures)
            ]

        # Filter out any failed downloads (None values)
        poster_images = [img for img in results if img is not None]

        font_path = get_font(google_font_url)

        if poster_images:
            safe_name = item_name.replace(" ", "_").replace("/", "_")
            output_path = f"/tmp/{safe_name}_cover.jpg"
            create_mosaic(poster_images, item_name, output_path, font_path)
        else:
            logger.warning(
                f"No posters available for item '{item_name}'. Skipping mosaic generation."
            )
            return

        self.set_poster(
            item_id=item_id,
            item_name=item_name,
            url=output_path,
        )

    def add_item_to_parent(
        self,
        parent_item_id: str,
        item: JellyfinItem,
        year_filter: bool = True,
        jellyfin_query_parameters: dict[str, str] | None = None,
    ) -> bool:
        """Adds an item to a parent item based on item name and release year"""

        media_type = (
            self.imdb_to_jellyfin_type_map.get(
                item["media_type"], item["media_type"]
            )
            if "media_type" in item and item["media_type"] is not None
            else []
        )

        params = {
            "enableTotalRecordCount": "false",
            "enableImages": "false",
            "Recursive": "true",
            "IncludeItemTypes": media_type,
            "searchTerm": item["title"],
            "fields": ["ProviderIds", "ProductionYear"],
        }

        params = {**params, **(jellyfin_query_parameters or {})}

        res = requests.get(
            f"{self.server_url}/Users/{self.user_id}/Items",
            headers={"X-Emby-Token": self.api_key},
            params=params,
        )

        items = cast(list[PItem], res.json()["Items"])

        # Check if there's an exact imdb_id match first
        match = None
        if "imdb_id" in item:
            for result in items:
                if result["ProviderIds"].get("Imdb", None) == item["imdb_id"]:
                    match = result
                    break

        elif "tmdb_id" in item:
            for result in items:
                if result["ProviderIds"].get("Tmdb", None) == item["tmdb_id"]:
                    match = result
                    break

        elif "tvdb_id" in item:
            for result in items:
                if result["ProviderIds"].get("Tvdb", None) == item["tvdb_id"]:
                    match = result
                    break

        elif "series" in item:
            for result in items:
                if result.get("SeriesName", None) == item["series"]:
                    match = result
                    break
        else:
            # Check if there's a year match
            if match is None and year_filter:
                for result in items:
                    if "release_year" in item and str(
                        result.get("ProductionYear", None)
                    ) == str(item["release_year"]):
                        match = result
                        break

            # Otherwise, just take the first result
            if match is None and len(items) == 1:
                match = items[0]

        if match is None:
            # Try searching all media types before assuming it does not exist
            # Only end when media_type is [], meaning we searched all media_types
            if len(media_type) != 0:
                return self.add_item_to_parent(
                    parent_item_id,
                    item={**item, "media_type": None},
                    year_filter=year_filter,
                    jellyfin_query_parameters=jellyfin_query_parameters,
                )
            else:
                logger.warning(
                    f"Item {item['title']} ({item.get('release_year', 'N/A')}) {item.get('imdb_id', '')} not found in jellyfin"
                )
                logger.debug(f"List Candidate: {item}")
                logger.debug(f"JF Search: {res.json()['Items']}")
            return False
        else:
            try:
                item_id = match["Id"]
                if self.item_type == "collection":
                    _ = requests.post(
                        f"{self.server_url}/Collections/{parent_item_id}/Items?ids={item_id}",
                        headers={"X-Emby-Token": self.api_key},
                    )
                else:
                    _ = requests.post(
                        f"{self.server_url}/Playlists/{parent_item_id}/Items",
                        headers={"X-Emby-Token": self.api_key},
                        params={
                            "ids": item_id,
                            "userId": self.user_id,
                        },
                    )
                logger.info(f"Added {item['title']} to {self.item_type}")
                logger.debug(f"    List item: {item}")
                logger.debug(f"    Matched JF item: {match}")
                return True
            except json.decoder.JSONDecodeError:
                logger.error(
                    f"Error adding {item['title']} to collection - JSONDecodeError"
                )
        return False

    def clear_item(
        self,
        item_id: str,
    ):
        """Clears a collection by removing all items from it"""
        res = requests.get(
            f"{self.server_url}/Users/{self.user_id}/Items",
            headers={"X-Emby-Token": self.api_key},
            params={"Recursive": "true", "parentId": item_id},
        )
        all_ids = [item["Id"] for item in res.json()["Items"]]

        # chunk ids into groups of 10
        all_ids = [all_ids[i : i + 10] for i in range(0, len(all_ids), 10)]
        for ids in all_ids:
            if self.item_type == "collection":
                _ = requests.delete(
                    f"{self.server_url}/Collections/{item_id}/Items",
                    headers={"X-Emby-Token": self.api_key},
                    params={"ids": ",".join(ids)},
                )
            else:
                _ = requests.delete(
                    f"{self.server_url}/Playlists/{item_id}/Items",
                    headers={"X-Emby-Token": self.api_key},
                    params={"entryIds": ",".join(ids)},
                )

        logger.info(f"Cleared collection {item_id}")
