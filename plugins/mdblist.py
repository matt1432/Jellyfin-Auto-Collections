import bs4
import requests

from utils.base_plugin import ListScraper


class MDBList(ListScraper):
    _alias_ = "mdblist"

    def get_list(self, list_id, config):
        list_id = list_id.strip("/")

        # Get the list name
        r = requests.get(f"https://mdblist.com/lists/{list_id}")
        soup = bs4.BeautifulSoup(r.text, "html.parser")
        list_name = soup.find("div", class_="ui form").find("h3").text.strip()  # type: ignore
        description = (
            soup.find("div", {"class": "ui form"})
            .find("div", {"class": "fourteen wide field"})  # type: ignore
            .find_all("p")  # type: ignore
        )
        description = "\n".join([p.text for p in description])

        # Get the list items
        r = requests.get(f"https://mdblist.com/lists/{list_id}/json")
        movies = r.json()
        movies = [
            {**movie, "media_type": movie["mediatype"]} for movie in movies
        ]

        return {"name": list_name, "items": movies, "description": description}
