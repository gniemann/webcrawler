"""
This module defines the PageNode class - which represents a single page (along with all it's links)
The module defines functions for retrieving pages, parsing pages to extract links, and the Favicon cache, all of
which is used internally by PageNode

PageNode should be the only thing that needs to be imported from this module
"""
import hashlib
import logging
import re

from site_utils import retrieve_url, save_file

link_regex = re.compile(r'''<a [^>]*href=['"]?(?P<link>(https?://)?([a-z0-9\-]+\.){1,}[a-z0-9]+(?<!\.html)((\?|/)[^'" ]*)?)['" ]''', re.I)
"""
Explanation of regex:
<a [^>]*href=['"]?(?P<link>(https?://))?([a-z0-9\-]+\.){1,2}[a-z0-9]+(?<!\.html)((\?|/)[^'" ]*)?)['" ]

Start with an anchor '<a ', followed by a any number of other characters except the closing >
until 'href=' is encountered

Match either ' or " or no quotes
Name the resulting link (the group in the outer most paranthesis) 'link' for easy identification later

Links can start with http:// or https://, but don't have to (match 0 or 1 times)
Links must have a group of alphanumberic + '-' characters, followed by a '.'. Links must have EITHER 1 or 2 of these

EX: github.com has 1 set of characters followed by a period, www.google.com has two

Following the last period, links must have another set of alphanumeric + '-' characters

(?<!\.html) lets us look at the last 5 characters. If they are .html, this must be a local link in teh form
somepage.html, in which case we do not want this link, so do not match

Links can end there, but don't have to. ((\?|/)[^'" ]*)? gets further links (optional)

(\?|/) first matches either ? (for query strings) or / (for routes)
[^'" ]* than matches any number of characters of any kind until it reaches a quote or space. The final ? means this
entire part is optional

The final ['" ] matches the closing quote or space.
"""

# regex to match just the host (including leading http...)
host_regex = re.compile(r'''https?://([a-z0-9\-]+\.){1,}[a-z0-9]+''', re.IGNORECASE)

# regex to extract an icon link from the <head> of a 404 error page
icon_regex = re.compile(r'''<link [^>]*rel="icon" [^>]*href=['"]?(?P<icon>[^'" ]*)[^>]*>''', re.IGNORECASE)


def make_phrase_regex(phrase):
    """
    Creates a regular expression for finding a phrase. The phrase is case-insensitive, can end with puncuation,
    and can be in quotes or parenthesis.
    :param phrase: phrase to build the regex for
    :return: a regular expression object
    """
    return re.compile(r'''['"( ]''' + phrase + r'''[\.?!)'" ]''', re.IGNORECASE)

def to_utf8(str_or_unicode):
    return unicode(str_or_unicode, 'utf-8', errors='replace')


def get_host(url):
    """Extracts and returns just the service + host from url"""
    return host_regex.match(url).group()


def extract_links(page):
    page = to_utf8(page)
    return [match.group('link') for match in link_regex.finditer(page) if match]


class Favicon:
    """
    This is a Singleton class which implements a favicon cache.
    """
    host_to_hash = {}
    hash_set = set()
    BASE = 'https://gammacrawler.appspot.com/favicons/'

    @classmethod
    def get_favicon(cls, url):

        host = get_host(url)
        host_key = host[host.find('//')+2:]

        if host_key in cls.host_to_hash:
            icon_hash = cls.host_to_hash[host_key]
            if icon_hash:
                filename = icon_hash + '.ico'
                return cls.BASE + filename
            else:
                return None

        favicon_url = host + '/favicon.ico'

        res = retrieve_url(favicon_url)

        if res.status_code == 200:
            icon = res.content
            icon_hash = hashlib.md5(icon).hexdigest()

            cls.host_to_hash[host_key] = icon_hash
            if icon_hash not in cls.hash_set:
                # save the file
                save_file(icon, icon_hash + '.ico')
                cls.hash_set.add(icon_hash)

            return cls.BASE + icon_hash + '.ico'

        elif res.status_code == 404:
            match = icon_regex.search(res.content)
            if match:
                icon_url = match.group('icon')
                if icon_url.startswith('/'):
                    icon_url = host + icon_url

                return cls.get_favicon(icon_url)
            else:
                cls.host_to_hash[host_key] = None
                return None
        else:
            cls.host_to_hash[host_key] = None
            return None


class PageNode(object):
    """This class represents a page 'node' in the tree graph.
    id is the assigned ID number
    url is the page url
    favicon, if present, is the url to the site's favicon
    parent is the ID of the parent node. None denotes a root node

    on creation, loads the page and parses links

    jsonify() - returns a JSON-able representation of the node"""

    __slots__ = ('id', 'depth', 'parent', 'phrase_found', 'url', '_links', 'favicon', 'end_phrase')

    @classmethod
    def make_pagenode(cls, *args, **kwargs):
        try:
            return cls(*args, **kwargs)
        except TypeError:
            return None
        except UnicodeEncodeError:
            return None

    def __init__(self, id, url, parent=None, end_phrase=None):
        """
        Initializes the PageNode. Specifically, requests the page, and if the request fails, will throw an exception
        :param id: Either a callable which generates ID numbers, or a suitable ID
        :param url: URL of the page this node will represent
        :param parent: The parent PageNode. Default of None signifies the root node
        :param end_phrase: Optional termination phrase
        """
        # retrive the URL first. We won't bother doing anything else if we can't get the page
        # if the URL starts with //, cut it off
        if url.startswith('//'):
            url = url[2:]
        # Ensure that our link starts with http
        if not url.startswith('http'):
            url = 'http://' + url

        self.url = url

        # attempt to load the page data. If it fails, the exception will perculate up (which is what we want)
        self.load()

        self.favicon = Favicon.get_favicon(self.url)

        # we got the page, so do the rest of the processing
        if callable(id):
            self.id = id()
        else:
            self.id = id

        if parent:
            self.parent = parent.id
            self.depth = parent.depth + 1
        else:
            self.parent = None
            self.depth = 0


    def load(self, end_phrase=None):
        """
        Loads the page, extracts the links, gets the favicon and looks for the end phrase
        :param end_phrase: end_phrase to search for. Only useful when called from __init__
        :return: nothing, but throws a TypeError when page retrieval fails
        """
        logging.debug("Retrieving {}".format(self.url))

        res = retrieve_url(self.url)

        # if we could not retrieve a page, raise an exception to ensure that this page is not created
        if res is None or res.status_code != 200:
            raise TypeError("Page is not retrievable")

        host = get_host(self.url)
        self._links = [link for link in extract_links(res.content) if not link.startswith(host)]

        if end_phrase and make_phrase_regex(end_phrase).search(res.content):
            self.phrase_found = True
        else:
            self.phrase_found = False


    def jsonify(self):
        return dict({'id': self.id,
                     'parent': self.parent,
                     'url': self.url,
                     'favicon': self.favicon,
                     'depth': self.depth})

    def __repr__(self):
        return "PageNode(id={}, parent={}, url={}, depth={})".format(self.id, self.parent, self.url, self.depth)

    def __getstate__(self):
        return {
            'id': self.id,
            'depth': self.depth,
            'parent': self.parent,
            'url': self.url,
            'favicon': self.favicon
        }

    def __setstate__(self, state):
        for key in self.__slots__:
            self.__setattr__(key, None)
        for key, val in state.items():
            self.__setattr__(key, val)

    def __iter__(self):
        return iter(self.links)
    
    @property
    def links(self):
        if self._links is None:
            self.load(self.end_phrase)

        return self._links
