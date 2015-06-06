"""
    SALTS XBMC Addon
    Copyright (C) 2014 tknorris

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import scraper
import urllib
import urlparse
import re
import xbmcaddon
import urllib2
from salts_lib import dom_parser
from salts_lib.constants import VIDEO_TYPES
from salts_lib.constants import QUALITIES

BASE_URL = 'http://www.mintmovies.net'
FORMATS = {'m18': QUALITIES.MEDIUM, 'm22': QUALITIES.HD720, 'm37': QUALITIES.HD1080}

class MintMovies_Scraper(scraper.Scraper):
    base_url = BASE_URL

    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.base_url = xbmcaddon.Addon().getSetting('%s-base_url' % (self.get_name()))

    @classmethod
    def provides(cls):
        return frozenset([VIDEO_TYPES.MOVIE])

    @classmethod
    def get_name(cls):
        return 'MintMovies'

    def resolve_link(self, link):
        return link

    def format_source_label(self, item):
        return '[%s] %s' % (item['quality'], item['host'])

    def get_sources(self, video):
        source_url = self.get_url(video)
        hosters = []
        if source_url:
            url = urlparse.urljoin(self.base_url, source_url)
            html = self._http_get(url, cache_limit=.5)
            fragment = ''
            match = re.search("replaceWith\('([^']+)", html)
            if match:
                fragment = match.group(1).replace('\\x', '').decode('hex')
            else:
                element = dom_parser.parse_dom(html, 'video')
                if element:
                    fragment = element[0]
                
            match = re.search('src="([^"]+)', fragment)
            if match:
                link = match.group(1)
                link_format = link[-3:]
                hoster = {'multi-part': False, 'host': self.get_name(), 'class': self, 'quality': FORMATS[link_format], 'views': None, 'rating': None, 'url': link, 'direct': True}
                hosters.append(hoster)
                
                # check for other resolutions
                formats = FORMATS
                del formats[link_format]
                for test_format in formats:
                    test_link = link.replace(link_format, test_format)
                    try:
                        urllib2.urlopen(test_link)
                        hoster = {'multi-part': False, 'host': self.get_name(), 'class': self, 'quality': FORMATS[test_format], 'views': None, 'rating': None, 'url': test_link, 'direct': True}
                        hosters.append(hoster)
                    except urllib2.HTTPError: pass

        return hosters

    def get_url(self, video):
        return super(MintMovies_Scraper, self)._default_get_url(video)

    def search(self, video_type, title, year):
        search_url = urlparse.urljoin(self.base_url, '/?s=')
        search_url += urllib.quote_plus(title)
        html = self._http_get(search_url, cache_limit=.25)
        results = []
        elements = dom_parser.parse_dom(html, 'div', {'class': 'movief'})
        for element in elements:
            match = re.search('href="([^"]+)">([^<]+)', element, re.DOTALL)
            if match:
                url, match_title_year = match.groups()
                match = re.search('(.*?)(?:\s+\(?(\d{4})\)?)', match_title_year)
                if match:
                    match_title, match_year = match.groups()
                else:
                    match_title = match_title_year
                    match_year = ''

                if not year or not match_year or year == match_year:
                    result = {'title': match_title, 'year': match_year, 'url': url.replace(self.base_url, '')}
                    results.append(result)
        return results

    def _http_get(self, url, data=None, cache_limit=8):
        return super(MintMovies_Scraper, self)._cached_http_get(url, self.base_url, self.timeout, data=data, cache_limit=cache_limit)
