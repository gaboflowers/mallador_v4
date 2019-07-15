import abc

class QueryEngine(abc.ABC):

    def __init__(self, source):
        self.source = source
        super().__init__()

    @abc.abstractmethod
    def query(self, inquired, **kwargs):
        fetch_function = kwargs.get('fetch_function', self.fetch)
        parse_function = kwargs.get('parse_function', self.parse)
        fetch_kwargs = kwargs.get('fetch_kwargs', {})
        parse_kwargs = kwargs.get('parse_kwargs', {})
        response = fetch_function(inquired, **fetch_kwargs)
        return parse_function(response, inquired, **parse_kwargs)


    @abc.abstractmethod
    def fetch(self, inquired=None, **kwargs):
        return None

    @abc.abstractmethod
    def parse(self, response=None, inquired=None, **kwargs):
        return None




