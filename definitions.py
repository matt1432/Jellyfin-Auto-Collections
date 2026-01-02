from typing import TypedDict


class JellyfinConfig(TypedDict):
    server_url: str
    api_key: str
    user_id: str


class JellyseerrConfig(TypedDict):
    api_key: str
    server_url: str
    email: str
    password: str
    user_type: str


class ListIDItem(TypedDict, total=False):
    list_name: str
    list_id: str
    list_desc: str


class BasePluginConfig(TypedDict, total=False):
    enabled: bool
    list_ids: list[str | ListIDItem]
    clear_collection: bool


class LetterboxdPluginConfig(BasePluginConfig):
    imdb_id_filter: bool


class TraktPluginConfig(BasePluginConfig):
    client_id: str
    client_secret: str


class ArrServerConfig(TypedDict):
    base_url: str
    api_key: str


class ArrPluginConfig(BasePluginConfig):
    server_configs: list[ArrServerConfig]


class JellyfinPluginConfig(BasePluginConfig):
    server_url: str
    api_key: str
    user_id: str


class PluginsConfig(TypedDict, total=False):
    imdb_chart: BasePluginConfig
    imdb_list: BasePluginConfig
    letterboxd: LetterboxdPluginConfig
    mdblist: BasePluginConfig
    tspdt: BasePluginConfig
    trakt: TraktPluginConfig
    arr: ArrPluginConfig
    jellyfin_api: JellyfinPluginConfig
    popular_movies: BasePluginConfig
    criterion_channel: BasePluginConfig
    listmania: BasePluginConfig
    bfi: BasePluginConfig


class _Config(TypedDict):
    jellyfin: JellyfinConfig
    plugins: PluginsConfig


class Config(_Config, total=False):
    crontab: str
    timezone: str
    jellyseerr: JellyseerrConfig


class _JellyfinItem(TypedDict):
    title: str
    release_year: int | None


class JellyfinItem(_JellyfinItem, total=False):
    media_type: str
    imdb_id: str | None


class PluginResult(TypedDict):
    name: str
    description: str
    items: list[JellyfinItem]
