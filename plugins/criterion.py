import bs4
import requests

from utils.base_plugin import ListScraper


class CriterionChannel(ListScraper):
    _alias_ = "criterion_channel"

    def get_list(self, list_id, config):
        r = requests.get(f"https://www.criterionchannel.com/{list_id}")
        soup = bs4.BeautifulSoup(r.text, "html.parser")

        list_name = soup.find("h1", class_="collection-title").text.strip()  # type: ignore
        description = soup.find(
            "div", class_="collection-description"
        ).text.strip()  # type: ignore

        items = []
        for item in soup.find_all("li", class_="js-collection-item"):
            title = item.find("strong").text.strip()  # type: ignore
            year = item.find("p")
            if year is not None and "•" in year.text:
                year = year.text.split("•")[1].strip()
            items.append(
                {"title": title, "release_year": year, "media_type": "movie"}
            )
        return {"name": list_name, "items": items, "description": description}
