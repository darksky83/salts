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
import urlparse
import urllib
import re
from salts_lib import kodi
from salts_lib import log_utils
from salts_lib import dom_parser
from salts_lib.constants import VIDEO_TYPES
from salts_lib.constants import FORCE_NO_MATCH

BASE_URL = 'http://www.moviexk.net'

class MoxieXK_Scraper(scraper.Scraper):
    base_url = BASE_URL

    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.base_url = kodi.get_setting('%s-base_url' % (self.get_name()))

    @classmethod
    def provides(cls):
        return frozenset([VIDEO_TYPES.TVSHOW, VIDEO_TYPES.EPISODE, VIDEO_TYPES.MOVIE])

    @classmethod
    def get_name(cls):
        return 'MovieXK'

    def resolve_link(self, link):
        return link

    def format_source_label(self, item):
        return '[%s] %s' % (item['quality'], item['host'])

    def get_sources(self, video):
        source_url = self.get_url(video)
        sources = []
        if source_url and source_url != FORCE_NO_MATCH:
            url = urlparse.urljoin(self.base_url, source_url)
            html = self._http_get(url, cache_limit=.5)
#             source = {'multi-part': False, 'url': url, 'host': host, 'class': self, 'quality': quality, 'views': None, 'rating': None, 'direct': direct}
#             sources.append(source)

        return sources

    def get_url(self, video):
        return self._default_get_url(video)

    def search(self, video_type, title, year):
        results = []
        search_url = urlparse.urljoin(self.base_url, '/search/')
        search_url += urllib.quote_plus(title)
        html = self._http_get(search_url, cache_limit=1)
        for fragment in dom_parser.parse_dom(html, 'div', {'class': 'inner'}):
            name = dom_parser.parse_dom(fragment, 'div', {'class': 'name'})
            if name:
                match = re.search('href="([^"]+)[^>]+>(.*?)</a>', name[0])
                if match:
                    match_url, match_title_year = match.groups()
                    
                    match_title_year = re.sub('</?[^>]*>', '', match_title_year)
                    match_title_year = re.sub('[Ww]atch\s+[Mm]ovie\s*', '', match_title_year)
                    match_title_year = match_title_year.replace('&#8217;', "'")
                    match = re.search('(.*?)\s+\((\d{4})[^)]*\)$', match_title_year)
                    if match:
                        match_title, match_year = match.groups()
                    else:
                        match_title = match_title_year
                        match_year = ''
    
                    if not match_year:
                        year_span = dom_parser.parse_dom(fragment, 'span', {'class': 'year'})
                        if year_span:
                            year_text = dom_parser.parse_dom(year_span[0], 'a')
                            if year_text:
                                match_year = year_text[0].strip()
    
                    if not year or not match_year or year == match_year:
                        result = {'title': match_title, 'url': self._pathify_url(match_url), 'year': match_year}
                        results.append(result)

        return results

    def _get_episode_url(self, show_url, video):
        season_url = show_url + '/season/%s' % (video.season)
        episode_pattern = 'href="([^"]+/season/%s/episode/%s/?)"' % (video.season, video.episode)
        title_pattern = 'href="(?P<url>[^"]+/season/%s/episode/%s/?)"\s+title="(?P<title>[^"]+)'
        return self._default_get_episode_url(season_url, video, episode_pattern, title_pattern)
