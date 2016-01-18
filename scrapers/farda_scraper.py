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
import re
from salts_lib import kodi
from salts_lib import log_utils
from salts_lib.constants import VIDEO_TYPES
from salts_lib.constants import FORCE_NO_MATCH

BASE_URL = 'http://dl.fardadownload.ir/'

class MovieFarsi_Scraper(scraper.Scraper):
    base_url = BASE_URL

    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.base_url = kodi.get_setting('%s-base_url' % (self.get_name()))

    @classmethod
    def provides(cls):
        return frozenset([VIDEO_TYPES.TVSHOW, VIDEO_TYPES.EPISODE, VIDEO_TYPES.MOVIE])

    @classmethod
    def get_name(cls):
        return 'FardaDownload'

    def resolve_link(self, link):
        return link

    def format_source_label(self, item):
        if 'format' in item:
            label = '[%s] (%s) %s' % (item['quality'], item['format'], item['host'])
        else:
            label = '[%s] %s' % (item['quality'], item['host'])
        if 'size' in item:
            label += ' (%s)' % (item['size'])
        return label

    def get_sources(self, video):
        source_url = self.get_url(video)
        hosters = []
        norm_title = self._normalize_title(video.title)
        if source_url and source_url != FORCE_NO_MATCH:
            source_url = urlparse.urljoin(self.base_url, source_url)
            for movie in self.__get_files(source_url, cache_limit=24):
                match_title, _match_year, height, extra = self._parse_movie_link(movie['link'])
                if 'dubbed' in extra.lower(): continue
                if not movie['directory'] and norm_title in self._normalize_title(match_title):
                    log_utils.log(movie)
                    stream_url = movie['url'] + '|User-Agent=%s' % (self._get_ua())
                    hoster = {'multi-part': False, 'host': self._get_direct_hostname(stream_url), 'class': self, 'quality': self._height_get_quality(height), 'views': None, 'rating': None, 'url': stream_url, 'direct': True}
                    if 'x265' in extra: hoster['format'] = 'x265'
                    if 'size' in movie: hoster['size'] = self._format_size(int(movie['size']))
                    hosters.append(hoster)
            
        return hosters

    def get_url(self, video):
        return super(MovieFarsi_Scraper, self)._default_get_url(video)

    def _get_episode_url(self, show_url, video):
        force_title = self._force_title(video)
        if not force_title:
            html = self._http_get(show_url, cache_limit=24)
            match = re.search('href="(S%02d/?)"' % (int(video.season)), html)
            if match:
                season_url = urlparse.urljoin(show_url, match.group(1))
                for item in self.__get_files(season_url, cache_limit=1):
                    match = re.search('(\.|_| )S%02d(\.|_| )?E%02d(\.|_| )' % (int(video.season), int(video.episode)), item['title'], re.I)
                    if match:
                        return season_url
            
    def search(self, video_type, title, year):
        results = []
        norm_title = self._normalize_title(title)
        if video_type == VIDEO_TYPES.MOVIE:
            if year:
                base_url = urlparse.urljoin(self.base_url, '/Film/')
                html = self._http_get(base_url, cache_limit=48)
                for link in self.__parse_directory(html):
                    if year == link['title']:
                        url = urlparse.urljoin(base_url, link['link'])
                        for movie in self.__get_files(url, cache_limit=24):
                            log_utils.log(movie)
                            match_title, match_year, _height, _extra = self._parse_movie_link(movie['link'])
                            if not movie['directory'] and norm_title in self._normalize_title(match_title) and (not year or not match_year or year == match_year):
                                result = {'url': self._pathify_url(url), 'title': match_title, 'year': year}
                                results.append(result)
        else:
            base_url = urlparse.urljoin(self.base_url, '/Serial/')
        return results

    def __get_files(self, url, cache_limit=.5):
        sources = []
        for row in self.__parse_directory(self._http_get(url, cache_limit=cache_limit)):
            source_url = urlparse.urljoin(url, row['link'])
            if row['directory']:
                sources += self.__get_files(source_url)
            else:
                row['url'] = source_url
                sources.append(row)
        return sources
    
    def __parse_directory(self, html):
        rows = []
        for match in re.finditer('\s*<a\s+href="([^"]+)">([^<]+)</a>\s+(\d+-[a-zA-Z]+-\d+ \d+:\d+)\s+(-|\d+)', html):
            link, title, date, size = match.groups()
            if title.endswith('/'): title = title[:-1]
            row = {'link': link, 'title': title, 'date': date}
            if link.endswith('/'):
                row['directory'] = True
            else:
                row['directory'] = False

            if size == '-':
                row['size'] = None
            else:
                row['size'] = size
            rows.append(row)
        return rows
