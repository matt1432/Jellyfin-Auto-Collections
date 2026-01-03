import argparse
import os
import sys
from typing import cast

import pluginlib
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from pyaml_env import parse_config

from definitions import (
    BasePluginConfig,
    Config,
    JellyfinImageType,
    ListScraperClass,
)
from utils.jellyfin import JellyfinClient
from utils.jellyseerr import JellyseerrClient


class Namespace(argparse.Namespace):
    config: str = "config.yaml"


parser = argparse.ArgumentParser(description="Jellyfin List Scraper")
_ = parser.add_argument(
    "--config", type=str, help="Path to config file", default="config.yaml"
)
args = parser.parse_args(namespace=Namespace())

# Set logging level
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
# Configure Loguru logger
logger.remove()  # Remove default configuration
_ = logger.add(sys.stderr, level=log_level)

# Load config
if not os.path.exists(args.config):
    logger.error(f"{args.config} does not exist.")
    logger.error(
        f"Copy config.yaml.example to {args.config} and add your jellyfin config."
    )
    raise Exception("No config file found.")
config = cast(Config, parse_config(args.config))


def main(config: Config):
    # Setup jellyfin connection
    jf_client = JellyfinClient(
        server_url=config["jellyfin"]["server_url"],
        api_key=config["jellyfin"]["api_key"],
        user_id=config["jellyfin"]["user_id"],
    )

    if "jellyseerr" in config:
        js_client = JellyseerrClient(
            server_url=config["jellyseerr"].get("server_url") or "",
            api_key=config["jellyseerr"].get("api_key", None),
            email=config["jellyseerr"].get("email", None),
            password=str(config["jellyseerr"].get("password", None)),
            user_type=str(config["jellyseerr"].get("user_type", "local")),
        )
    else:
        js_client = None

    # Load plugins
    loader = pluginlib.PluginLoader(modules=["plugins"])
    plugins = cast(
        dict[str, type[ListScraperClass]], loader.plugins["list_scraper"]
    )

    # If Jellyfin_api plugin is enabled - pass the jellyfin creds to it
    if "jellyfin_api" in config["plugins"] and config["plugins"][
        "jellyfin_api"
    ].get("enabled", False):
        config["plugins"]["jellyfin_api"]["server_url"] = config["jellyfin"][
            "server_url"
        ]
        config["plugins"]["jellyfin_api"]["user_id"] = config["jellyfin"][
            "user_id"
        ]
        config["plugins"]["jellyfin_api"]["api_key"] = config["jellyfin"][
            "api_key"
        ]

    # Update jellyfin with lists
    for plugin_name in config["plugins"]:
        plugin_config = cast(BasePluginConfig, config["plugins"][plugin_name])
        if (
            "enabled" in plugin_config
            and plugin_config["enabled"]
            and "list_ids" in plugin_config
            and plugin_name in plugins
        ):
            for list_entry in plugin_config["list_ids"]:
                if isinstance(list_entry, str):
                    list_id = list_entry
                    list_name = None
                    list_images = None
                else:
                    if "list_id" in list_entry:
                        list_id = list_entry["list_id"]
                    else:
                        list_id = str(list_entry)

                    list_images = (
                        list_entry["images"]
                        if "images" in list_entry
                        and isinstance(list_entry["images"], dict)  # pyright: ignore[reportUnnecessaryIsInstance]
                        else None
                    )

                    list_name = list_entry.get("list_name", None)

                logger.info("")
                logger.info("")
                logger.info(
                    f"Getting list info for plugin: {plugin_name}, list id: {list_id}"
                )

                # Match list items to jellyfin items
                list_info = plugins[plugin_name].get_list(
                    list_entry, plugin_config
                )

                # Find jellyfin collection or create it
                collection_id = jf_client.find_collection_with_name_or_create(
                    list_name or list_info["name"],
                    list_id,
                    list_info.get("description", None),
                    plugin_name,
                )

                if plugin_config.get("clear_collection", False):
                    # Optionally clear everything from the collection first
                    jf_client.clear_collection(collection_id)

                # Add items to the collection
                for item in list_info["items"]:
                    matched = jf_client.add_item_to_collection(
                        collection_id,
                        item,
                        year_filter=plugin_config.get("year_filter", True),
                        jellyfin_query_parameters=config["jellyfin"].get(
                            "query_parameters", {}
                        ),
                    )
                    if not matched and js_client is not None:
                        js_client.make_request(item)

                if list_images is not None:
                    for image_type, path_or_url in list_images.items():
                        parsed_type = image_type.lower().capitalize()

                        if (
                            parsed_type
                            in JellyfinImageType.__members__.values()
                        ):
                            jf_client.set_poster(
                                collection_id=collection_id,
                                collection_name=list_name or list_info["name"],
                                image_type=JellyfinImageType(parsed_type),
                                url=path_or_url,
                            )

                # Add a poster image if collection doesn't have one
                elif not jf_client.has_poster(collection_id):
                    logger.info("Collection has no poster - generating one")
                    jf_client.make_poster(collection_id, list_info["name"])


if __name__ == "__main__":
    logger.info("Starting up")
    logger.info("Starting initial run")
    main(config)

    # Setup scheduler
    if "crontab" in config and config["crontab"] != "":
        scheduler = BlockingScheduler()
        _ = scheduler.add_job(
            main,
            CronTrigger.from_crontab(config["crontab"]),
            args=[config],
            timezone=config.get("timezone", "UTC"),
        )
        logger.info("Starting scheduler using crontab: " + config["crontab"])
        scheduler.start()
