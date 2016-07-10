import logging
import re

from google.appengine.api import urlfetch

link_regex = re.compile(
    r'''<a [^>]*href=['"]?(?P<link>(https?://)?([a-z0-9\-]+\.){1,2}[a-z0-9]+(?<!\.html)((\?|/)[^'" ]*)?)['" ]''', re.I)
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
host_regex = re.compile(r'''https?://([a-z0-9\-]+\.){1,2}[a-z0-9]+''')


def make_phrase_regex(phrase):
    return re.compile(r'''['"( ]''' + phrase + r'''[\.?!)'" ]''', re.IGNORECASE)


def retrieve_url(url):
    """Attempts to GET the url. If unsuccessful, returns None and lets the caller deal with it
    This function is designed to abstract away GAE specific code"""
    try:
        return urlfetch.fetch(url, deadline=10)
    except:
        logging.info("Unable to fetch URL: {}".format(url))
        return None


def to_utf8(str_or_unicode):
    return unicode(str_or_unicode, 'utf-8', errors='replace')


def get_host(url):
    """Extracts and returns just the service + host from url"""
    return host_regex.match(url).group()


def extract_links(page):
    page = to_utf8(page)
    return [match.group('link') for match in link_regex.finditer(page)]


class Favicon:
    cache = {}

    @classmethod
    def get_favicon(cls, url):
        host = get_host(url)

        if host in cls.cache:
            return cls.cache[host]

        favicon_url = host + '/favicon.ico'

        if retrieve_url(favicon_url):
            cls.cache[host] = favicon_url
            return favicon_url

        return None


class PageNode:
    """This class represents a page 'node' in the tree graph.
    id is the assigned ID number
    url is the page url
    favicon, if present, is the url to the site's favicon
    parent is the ID of the parent node. None denotes a root node

    on creation, loads the page and parses links

    jsonify() - returns a JSON-able representation of the node"""

    __slots__ = ('id', 'depth', 'parent', 'phrase_found', 'url', 'links', 'favicon')

    @classmethod
    def make_pagenode(cls, *args, **kwargs):
        try:
            return cls(*args, **kwargs)
        except TypeError:
            return None

    def __init__(self, id, url, parent=None, end_phrase=None):
        # retrive the URL first. We won't bother doing anything else if we can't get the page
        # if the URL starts with //, cut it off
        if url.startswith('//'):
            url = url[2:]
        # Ensure that our link starts with http
        if not url.startswith('http'):
            url = 'http://' + url

        logging.info("Retrieving {}".format(url))

        res = retrieve_url(url)

        # if we could not retrieve a page, raise an exception to ensure that this page is not created
        if res is None or res.status_code != 200:
            raise TypeError("Page is not retrievable")

        # we got the page, so do the rest of the processing
        if callable(id):
            self.id = id()
        else:
            self.id = id

        self.url = url

        if parent:
            self.parent = parent.id
            self.depth = parent.depth + 1
        else:
            self.parent = None
            self.depth = 0

        host = get_host(url)
        self.links = [link for link in extract_links(res.content) if not link.startswith(host)]

        if end_phrase and make_phrase_regex(end_phrase).search(res.content):
            self.phrase_found = True
        else:
            self.phrase_found = False

        self.favicon = Favicon.get_favicon(url)

    def jsonify(self):
        return dict({'id': self.id,
                     'parent': self.parent,
                     'url': self.url,
                     'favicon': self.favicon,
                     'depth': self.depth})
