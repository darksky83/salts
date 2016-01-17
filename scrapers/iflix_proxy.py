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
from salts_lib.trans_utils import i18n
from salts_lib import log_utils
try:
    import iflix_scraper
except Exception as e:
    log_utils.log('import failed: %s' % (e), log_utils.LOGDEBUG)

BASE_URL = 'http://cnfstudio.com'

class IFlix_Proxy(scraper.Scraper):
    base_url = BASE_URL
    
    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.exists = False
        self.__update_scraper_py('iflix_scraper.py')
        if self.exists:
            try:
                import iflix_scraper
                self.__scraper = iflix_scraper.Iflix_Scraper(timeout)
            except Exception as e:
                log_utils.log('Failure during %s scraper creation: %s' % (self.get_name(), e), log_utils.LOGWARNING)
                self.__scraper = None
   
    @classmethod
    def provides(cls):
        try:
            return iflix_scraper.Iflix_Scraper.provides()
        except:
            return frozenset([])
    
    @classmethod
    def get_name(cls):
        return 'IFlix'
    
    def resolve_link(self, link):
        if self.__scraper is not None:
            return self.__scraper.resolve_link(link)
    
    def format_source_label(self, item):
        if self.__scraper is not None:
            return self.__scraper.format_source_label(item)
    
    def get_sources(self, video):
        if self.__scraper is not None:
            return self.__scraper.get_sources(video)
            
    def get_url(self, video):
        if self.__scraper is not None:
            return self.__scraper.get_url(video)
    
    def search(self, video_type, title, year):
        if self.__scraper is not None:
            return self.__scraper.search(video_type, title, year)
        else:
            return []
    
    def _get_episode_url(self, show_url, video):
        if self.__scraper is not None:
            return self.__scraper._get_episode_url(show_url, video)

    @classmethod
    def get_settings(cls):
        name = cls.get_name()
        try:
            settings = iflix_scraper.Iflix_Scraper.get_settings()
            offset = 5
        except:
            settings = super(IFlix_Proxy, cls).get_settings()
            offset = 4
        settings.append('         <setting id="%s-scraper_url" type="text" label="    %s" default="" visible="eq(-%d,true)"/>' % (name, i18n('scraper_location'), offset))
        settings.append('         <setting id="%s-scraper_password" type="text" label="    %s" option="hidden" default="" visible="eq(-%d,true)"/>' % (name, i18n('scraper_key'), offset + 1))
        return settings
