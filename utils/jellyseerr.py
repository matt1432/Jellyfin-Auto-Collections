import urllib.parse
from typing import cast

import requests
from loguru import logger

from definitions import Config, JellyfinItem


class JellyseerrClient:
    api_key: str | None
    server_url: str
    session: requests.Session

    def __init__(
        self,
        server_url: str,
        api_key: str | None = None,
        email: str | None = None,
        password: str | None = None,
        user_type: str = "local",
    ):
        # Fix common url issues
        if server_url.endswith("/"):
            server_url = server_url[:-1]  # Remove trailing slash
        if not server_url.endswith("/api/v1"):
            server_url += "/api/v1"
        self.server_url = server_url

        if user_type not in ["local", "plex", "jellyfin"]:
            raise Exception(
                "Invalid user type. Must be one of: local, plex, jellyfin"
            )

        # Check if server is reachable
        try:
            r = requests.get(self.server_url + "/status")
            if r.status_code != 200:
                raise Exception("Jellyseerr Server is not reachable")
        except requests.exceptions.ConnectionError:
            raise Exception("Jellyseerr Server is not reachable")

        self.session = requests.Session()
        self.api_key = api_key
        if api_key is not None:
            r = self.session.headers.update({"X-Api-Key": api_key})
            if r is None or r.status_code != 200:
                raise Exception("Invalid jellyseerr API Key")
        if email is not None and password is not None:
            r = self.session.post(
                f"{self.server_url}/auth/{user_type}",
                json={"email": email, "password": password},
            )
            if r.status_code != 200:
                raise Exception("Invalid jellyseerr email or password")

        # Check if user is authenticated
        r = self.session.get(f"{self.server_url}/auth/me")
        if r.status_code != 200:
            raise Exception("jellyseerr user is not authenticated")

    def make_request(self, item: JellyfinItem):
        """Request item from jellyseerr"""

        # Search for item
        r = self.session.get(
            f"{self.server_url}/search",
            params={"query": urllib.parse.quote_plus(item["title"])},
        )

        # Find matching item
        mediaId = None
        result = None
        for _result in r.json()["results"]:
            result = _result
            # Try IMDB match first
            if "mediaInfo" in result and "ImdbId" in result["mediaInfo"]:
                imdb_id = result["mediaInfo"]["ImdbId"]
                if "imdb_id" in item and imdb_id == item["imdb_id"]:
                    mediaId = result["id"]
                    logger.debug(f"Found exact IMDB match for {item['title']}")
                    break
            elif "releaseDate" in result:
                # Try year match
                release_year = result["releaseDate"].split("-")[0]
                if release_year == str(item["release_year"]).strip():
                    mediaId = result["id"]
                    logger.debug(f"Found year match for {item['title']}")
                    break

        # Request item if not found
        if mediaId is not None and result is not None:
            if (
                "mediaInfo" not in result
                or result["mediaInfo"]["jellyfinMediaId"] is None
            ):
                # If it's not already in Jellyfin
                # Request item
                r = self.session.post(
                    f"{self.server_url}/request",
                    json={
                        "mediaType": result["mediaType"],
                        "mediaId": mediaId,
                    },
                )
                logger.info(f"Requested {item['title']} from Jellyseerr")


if __name__ == "__main__":
    from pyaml_env import parse_config

    config = cast(
        Config,
        parse_config(
            "/home/thomas/Documents/Jellyfin-Auto-Collections/config.yaml"
        ),
    )

    if "jellyseerr" not in config:
        raise Exception

    client = JellyseerrClient(
        server_url=config["jellyseerr"]["server_url"],
        api_key=config["jellyseerr"]["api_key"],
    )
    client.make_request(
        JellyfinItem(title="The Matrix", imdb_id="tt0133093", release_year=1999)
    )
