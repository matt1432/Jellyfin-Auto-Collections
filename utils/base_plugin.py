import pluginlib

@pluginlib.Parent('list_scraper')
class ListScraper(object):

    @pluginlib.abstractmethod
    def get_list(self, list_id, config):
        pass
