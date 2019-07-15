from .QueryEngine import QueryEngine
import urllib
import bs4
import re

re_three_nums = re.compile("(\d+).*?(\d+).*?(\d+)")
re_multiple_spaces = re.compile("[\n ]{2,}")

class DiraeEngine(QueryEngine):

    def __init__(self, **kwargs):
        self.max_simple_number = kwargs.get('max_simple_number', 10)
        self.max_match_number = kwargs.get('max_match_number', 5)

        self.fetch_kwargs = {}
        self.fetch_kwargs['timeout'] = kwargs.get('timeout', 15)
        
        super().__init__("https://dirae.es/palabras/")

    def query(self, inquired, **kwargs):
        show_matches = kwargs.get('show_matches', False)
        super_args = {}
        if show_matches:
            super_args['parse_function'] = self.parse_show_matches

        return super().query(inquired, **super_args)

    def fetch(self, inquired, **kwargs):
        params = urllib.parse.urlencode({'q':inquired})
        response = urllib.request.urlopen(self.source+"?"+params,
                                          **self.fetch_kwargs)
        return response

    def _parse_get_items(self, response):
        soup = bs4.BeautifulSoup(response, 'html.parser')
        ulist = soup.find('ul', {'id':'ul_results'})
        items = ulist.findAll('li',{'class':'sr'})
        return items

    def parse(self, response, **kwargs):
        items = self._parse_get_items(response)
        simple_items = [self._get_item_text(item) for item in items]
        if self.max_simple_number == 0:
            return simple_items
        return simple_items[:min(len(simple_items)-1, self.max_simple_number)]

    def parse_show_matches(self, response):
        items = self._parse_get_items(response)
        results = []
        for item in items:
            word = self._get_item_text(item)
            matches_div = item.find('div',{'class':'hl'})
            if matches_div is None:
                results.append([word,""])
                continue
            matches_txt = matches_div.decode_contents().strip()
            matches_txt = re_multiple_spaces.sub("", matches_txt)
            matches_txt = matches_txt.replace('<em>','*').replace('</em>','*')
            gs = re_three_nums.search(matches_txt)
            if gs and len(gs.groups()) >= 3:
                matches_txt = matches_txt[:gs.start(3)]
            result = [word, matches_txt]
            results.append(result)
        if self.max_match_number == 0:
            return results
        results = results[:min(len(results)-1, self.max_match_number)]
        return results

        
    def _get_item_text(self, item):
        return item.find('a', {'title':False}).text
