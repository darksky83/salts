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
import re
import urlparse
from salts_lib import kodi
from salts_lib import log_utils
from salts_lib import scraper_utils
from salts_lib.constants import FORCE_NO_MATCH
from salts_lib.constants import VIDEO_TYPES
from salts_lib.kodi import i18n
import scraper


VIDEO_EXT = ['MKV', 'AVI', 'MP4']
MIN_MEG = 100
LIST_URL = '/api/transfer/list'
BROWSE_URL = '/api/torrent/browse?hash=%s'

class PremiumizeV2_Scraper(scraper.Scraper):
    base_url = ''
    base_name = 'Premiumize.me'

    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout = timeout
        if kodi.get_setting('%s-use_https' % (self.__class__.base_name)) == 'true':
            scheme = 'https'
            prefix = 'www'
        else:
            scheme = 'http'
            prefix = 'http'
        base_url = kodi.get_setting('%s-base_url' % (self.__class__.base_name))
        self.base_url = scheme + '://' + prefix + '.' + base_url
        self.username = kodi.get_setting('%s-username' % (self.__class__.base_name))
        self.password = kodi.get_setting('%s-password' % (self.__class__.base_name))

    @classmethod
    def provides(cls):
        return frozenset([VIDEO_TYPES.MOVIE, VIDEO_TYPES.EPISODE])

    @classmethod
    def get_name(cls):
        return 'Premiumize.V2'

    def resolve_link(self, link):
        return link

    def format_source_label(self, item):
        label = '[%s] %s' % (item['quality'], item['host'])
        if 'size' in item:
            label += ' (%s)' % (item['size'])
        if 'extra' in item:
            label += ' [%s]' % (item['extra'])
        return label

    def get_sources(self, video):
        hosters = []
        source_url = self.get_url(video)
        if source_url and source_url != FORCE_NO_MATCH:
            query = urlparse.parse_qs(source_url)
            if 'hash' in query:
                url = urlparse.urljoin(self.base_url, BROWSE_URL % (query['hash'][0]))
                js_data = self._http_get(url, cache_limit=1)
                if 'content' in js_data:
                    videos = self.__get_videos(js_data['content'], video)
                    for video in videos:
                        host = self._get_direct_hostname(video['url'])
                        hoster = {'multi-part': False, 'class': self, 'views': None, 'url': video['url'], 'rating': None, 'host': host, 'quality': video['quality'], 'direct': True}
                        if 'size' in video: hoster['size'] = scraper_utils.format_size(video['size'])
                        if 'name' in video: hoster['extra'] = video['name']
                        hosters.append(hoster)
                         
        return hosters
    
    def __get_videos(self, content, video):
        videos = []
        for key in content:
            item = content[key]
            if item['type'].lower() == 'dir':
                videos += self.__get_videos(item['children'], video)
            else:
                if item['ext'].upper() in VIDEO_EXT and ('size' not in item or int(item['size']) > (MIN_MEG * 1024 * 1024)):
                    temp_video = {'name': item['name'], 'url': item['url'], 'size': item['size']}
                    temp_video['quality'] = self.__get_quality(item, video)
                    videos.append(temp_video)
                    if 'transcoded' in item and item['transcoded']:
                        transcode = item['transcoded']
                        name = '(Transcode) %s' % (item['name'])
                        temp_video = {'name': name, 'url': transcode['url']}
                        temp_video['quality'] = self.__get_quality(transcode, video)
                        if 'size' in transcode: temp_video['size'] = transcode['size']
                        videos.append(temp_video)
        return videos
    
    def __get_quality(self, item, video):
        if 'width' in item:
            return scraper_utils.width_get_quality(item['width'])
        elif 'height' in item:
            return scraper_utils.height_get_quality(item['height'])
        else:
            if video.video_type == VIDEO_TYPES.MOVIE:
                _title, _year, height, _extra = scraper_utils.parse_movie_link(item['name'])
            else:
                _title, _season, _episode, height, _extra = scraper_utils.parse_episode_link(item['name'])
            return scraper_utils.height_get_quality(height)
        
    def get_url(self, video):
        url = None
        self.create_db_connection()
        result = self.db_connection.get_related_url(video.video_type, video.title, video.year, self.get_name(), video.season, video.episode)
        if result:
            url = result[0][0]
            log_utils.log('Got local related url: |%s|%s|%s|%s|%s|' % (video.video_type, video.title, video.year, self.get_name(), url))
        else:
            if video.video_type == VIDEO_TYPES.MOVIE:
                results = self.search(video.video_type, video.title, video.year)
                if results:
                    url = results[0]['url']
                    self.db_connection.set_related_url(video.video_type, video.title, video.year, self.get_name(), url)
            else:
                url = self._get_episode_url(video)
                if url:
                    self.db_connection.set_related_url(video.video_type, video.title, video.year, self.get_name(), url, video.season, video.episode)

        return url

    def _get_episode_url(self, video):
        url = urlparse.urljoin(self.base_url, LIST_URL)
        js_data = self._http_get(url, cache_limit=0)
        norm_title = scraper_utils.normalize_title(video.title)
        if 'transfers' in js_data:
            airdate_fallback = kodi.get_setting('airdate-fallback') == 'true' and video.ep_airdate
            show_title = ''
            if not scraper_utils.force_title(video):
                for item in js_data['transfers']:
                    sxe_pattern = '(.*?)[. _]S%02dE%02d[. _]' % (int(video.season), int(video.episode))
                    match = re.search(sxe_pattern, item['name'], re.I)
                    if match:
                        show_title = match.group(1)
                    elif video.ep_airdate and airdate_fallback:
                        airdate_pattern = '(.*?)[. _]%s[. _]%02d[. _]%02d[. _]' % (video.ep_airdate.year, video.ep_airdate.month, video.ep_airdate.day)
                        match = re.search(airdate_pattern, item['name'])
                        if match:
                            show_title = match.group(1)
                    
                    if show_title and norm_title in scraper_utils.normalize_title(show_title):
                        return 'hash=%s' % (item['hash'])
                
    def search(self, video_type, title, year, season=''):
        url = urlparse.urljoin(self.base_url, LIST_URL)
        js_data = self._http_get(url, cache_limit=0)
        norm_title = scraper_utils.normalize_title(title)
        results = []
        if 'transfers' in js_data:
            for item in js_data['transfers']:
                if re.search('[._ ]S\d+E\d+[._ ]', item['name']): continue  # skip episodes for movies
                match = re.search('(.*?)\(?(\d{4})\)?(.*)', item['name'])
                if match:
                    match_title, match_year, extra = match.groups()
                else:
                    match_title, match_year, extra = item['name'], '', ''
                match_title = match_title.strip()
                extra = extra.strip()
                if norm_title in scraper_utils.normalize_title(match_title) and (not year or not match_year or year == match_year):
                    result_title = match_title
                    if extra: result_title += ' [%s]' % (extra)
                    result = {'title': result_title, 'year': match_year, 'url': 'hash=%s' % (item['hash'])}
                    results.append(result)
        
        return results

    @classmethod
    def get_settings(cls):
        name = cls.get_name()
        settings = [
            '         <setting id="%s-enable" type="bool" label="%s %s" default="true" visible="true"/>' % (name, name, i18n('enabled')),
            '         <setting id="%s-sub_check" type="bool" label="    %s" default="false" visible="eq(-1,true)"/>' % (name, i18n('page_existence')),
            '         <setting id="%s_last_results" type="number" default="0" visible="false"/>' % (name)
        ]
        return settings

    def _http_get(self, url, data=None, allow_redirect=True, cache_limit=8):
        if not self.username or not self.password:
            return {}
        
        if data is None: data = {}
        data.update({'customer_id': self.username, 'pin': self.password})
        result = super(self.__class__, self)._http_get(url, data=data, allow_redirect=allow_redirect, cache_limit=cache_limit)
        js_result = scraper_utils.parse_json(result, url)
        if 'status' in js_result and js_result['status'] == 'error':
            log_utils.log('Premiumize V2 Scraper Error: %s - (%s)' % (url, js_result.get('message', 'Unknown Error')), log_utils.LOGWARNING)
            js_result = {}
            
        return js_result
