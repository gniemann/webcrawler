"""
This module defines the PageNode class - which represents a single page (along with all it's links)
The module defines functions for retrieving pages, parsing pages to extract links, and the Favicon cache, all of
which is used internally by PageNode

PageNode should be the only thing that needs to be imported from this module
"""
import logging
import re

from site_utils import retrieve_url
from favicon import Favicon
from host import get_host

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

scripts_regex = re.compile(r'''<script.*?</script>''', re.IGNORECASE | re.DOTALL)
styles_regex = re.compile(r'''<style.*?</style>''', re.IGNORECASE | re.DOTALL)
words_regex = re.compile(r'''>(?P<words>[^<]+?)<''', re.IGNORECASE | re.DOTALL)

def make_phrase_regex(phrase):
    """
    Creates a regular expression for finding a phrase. The phrase is case-insensitive, can end with puncuation,
    and can be in quotes or parenthesis.
    :param phrase: phrase to build the regex for
    :return: a regular expression object
    """
    return re.compile(r'''['"( ]''' + phrase + r'''[\.\?!)'" ]''', re.IGNORECASE)

def to_utf8(str_or_unicode):
    return unicode(str_or_unicode, 'utf-8', errors='replace')


def extract_links(page):
    page = to_utf8(page)
    return [match.group('link') for match in link_regex.finditer(page) if match]

def phrase_in_page(page, phrase):
    content = page
    for script in scripts_regex.finditer(content):
        content = content.replace(script.group(), '')

    for style in styles_regex.finditer(content):
        content = content.replace(style.group(), '')

    for word_match in words_regex.finditer(content):
        words = to_utf8(word_match.group())
        if phrase in words:
            return True

    return False

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
        except RuntimeError:
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
        page_content = self.load(end_phrase)

        # attempt to get the favicon url with both the URL and the page content
        self.favicon = Favicon.get_favicon(self.url, page_content)

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
        :return: returns the content of the page
        throws a TypeError when page retrieval fails
        """
        logging.debug("Retrieving {}".format(self.url))

        res = retrieve_url(self.url)

        # if we could not retrieve a page, raise an exception to ensure that this page is not created
        if res is None or res.status_code != 200:
            raise RuntimeError("Page is not retrievable")

        host = get_host(self.url)
        self._links = list(set(link for link in extract_links(res.content) if not link.startswith(host)))

        if end_phrase and phrase_in_page(res.content, end_phrase):
            self.phrase_found = True
        else:
            self.phrase_found = False

        return res.content

    def jsonify(self):
        return dict({'id': self.id,
                     'parent': self.parent,
                     'url': self.url,
                     'favicon': self.favicon,
                     'depth': self.depth,
                     'phrase_found': self.phrase_found})

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
