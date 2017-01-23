

import hashlib
import io
import logging
import pickle
import re
import threading

from site_utils import retrieve_url, save_file, list_files, read_file
from host import get_host

# regex to extract an icon link from the <head> of a 404 error page
icon_regex = re.compile(r'''<link [^>]*rel=['"](shortcut )?icon['"] [^>]*href=['"]?\.?(?P<icon>[^'" ]*)[^>]*>''', re.IGNORECASE)


class FileCache(object):
    def __init__(self, data_cls, filename):
        self.new_count = 0
        self.filename = filename
        self.data = data_cls()

        self._load()

    def _load(self):
        logging.info('loading from {}'.format(self.filename))
        raw_data = read_file(self.filename)
        if raw_data is None:
            logging.info('Nothing loaded')
            return

        logging.info('Loaded from file')
        self.data = pickle.load(io.BytesIO(raw_data))

    def _save(self):
        logging.info('Saving to file {}'.format(self.filename))
        data = pickle.dumps(self.data)
        try:
            save_file(data, self.filename)
        except:
            pass
        else:
            self.new_count = 0

class HostToHashDict(FileCache):
    def __init__(self):
        super(type(self), self).__init__(dict, 'hash_dict')


    def __contains__(self, item):
        return item in self.data

    def __setitem__(self, key, value):
        if key not in self.data:
            self.data[key] = value
            self.new_count += 1

            if self.new_count > 5:
                self._save()

    def __getitem__(self, item):
        return self.data[item]


class HashSet(FileCache):
    def __init__(self):
        super(type(self), self).__init__(set, 'hash_set')

    def __contains__(self, item):
        return item in self.data

    def add(self, item):
        if item not in self.data:
            self.data.add(item)
            self.new_count += 1

            if self.new_count > 5:
                self._save()


class Favicon:
    """
    This is a Singleton class which implements a favicon cache.
    """
    host_to_hash = HostToHashDict()
    hash_set = HashSet()
    lock = threading.Lock()
    BASE = 'https://gammacrawler.appspot.com/favicons/'
    #BASE = 'http://localhost:8080/favicons/'

    cache_hits = 0
    total_requests = 0

    @classmethod
    def get_favicon(cls, url, page=None):
        """
        Retrieves and stores the site's favicon. Returns a local (on this server) URL to the stored favicon
        :param url: site for which we want a favicon
        :return: if a favicon is found, returns a URL to our locally served favicon.
        If no favicon is found, returns None
        """
        with cls.lock:
            cls.total_requests += 1.0
            host, host_key = cls._get_host_key(url)

            if host_key in cls.host_to_hash:
                cls.cache_hits += 1.0
                logging.info('Favicon cache hit! Hit percetage {:.2%}'.format(cls.cache_hits / cls.total_requests))
                icon_hash = cls.host_to_hash[host_key]
                if icon_hash:
                    filename = icon_hash + '.ico'
                    return cls.BASE + filename
                else:
                    return None

            logging.info('Favicon cache miss. Hit percetage {:.2%}'.format(cls.cache_hits / cls.total_requests))

            if page:
                # attempt to extract from the page first
                icon = cls._extract_favicon_from_page(page, url)

            # if either we didn't get passed the page, or no icon could be extracted, attempt the default route
            if not page or not icon:
                icon = cls._download_favicon(host + '/favicon.ico')

            if not icon:
                cls.host_to_hash[host_key] = None
                return None

            icon_hash = hashlib.md5(icon).hexdigest()
            cls.host_to_hash[host_key] = icon_hash

            if icon_hash not in cls.hash_set:
                save_file(icon, icon_hash + '.ico')
                cls.hash_set.add(icon_hash)

            return cls.BASE + icon_hash + '.ico'


    @classmethod
    def _get_host_key(cls, url):
        host = get_host(url)
        host_key = host[host.find('//')+2:]

        return host, host_key

    @classmethod
    def _download_favicon(cls, favicon_url, level=1):
        """
        Attempts to download a favicon. If successful, returns the favicon.
        If a 404 is returned, attempts to find a favicon link within the returned page. If one is found,
        attempts to retrieve and return that icon
        :param favicon_url: the URL of the icon to retrieve
        :return:
        """
        # prevents a form of infinite recursion
        if level > 3:
            return None

        res = retrieve_url(favicon_url)

        if res is None:
            return None
        elif res.status_code == 200:
            return res.content
        elif res.status_code == 404:
            return cls._extract_favicon_from_page(res.content, favicon_url, level+1)

        return None

    @classmethod
    def _extract_favicon_from_page(cls, page, url, level=1):

        # prevent a form of infinite recursion
        if level > 3:
            return None

        #first check the cache
        host, host_key = cls._get_host_key(url)

        match = icon_regex.search(page)
        if match:
            icon_url = match.group('icon')
            if icon_url.startswith('//'):
                icon_url = 'http:' + icon_url
            elif icon_url.startswith('/'):
                icon_url = get_host(url) + icon_url
            return cls._download_favicon(icon_url, level+1)
        else:
            return None
