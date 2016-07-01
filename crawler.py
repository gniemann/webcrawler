from pprint import pprint
import re

from google.appengine.api import urlfetch

class PageNode:
    """This class represents a page 'node' in the tree graph.
    id is the assigned ID number
    url is the page url
    favicon, if present, is the url to the site's favicon
    parent is the ID of the parent node. None denotes a root node

    jsonify() - returns a JSON-able representation of the node"""
    id_counter = 0
    def __init__(self, id, url, favicon=None, parent=None):
        self.id = id
        self.url = url
        self.favicon = favicon
        self.parent = parent

    def jsonify(self):
        data = {
            'id': self.id,
            'url': self.url,
            'favicon': self.favicon,
            'parent': self.parent
        }
        return data

link_regex = re.compile(r'''<a [^>]*href=['"]?(?P<link>(https?://)?([a-z0-9\-]+\.){1,2}[a-z0-9]+(?<!\.html)((\?|/)[^'" ]*)?)['" ]''', re.I)

def extract_links(page):
    return [match.group('link') for match in link_regex.finditer(page)]

def get_page(url, id, parent=None):
    """Retrieves the page pointed to by URL, extracts the links, and returns a tuple of a PageNode of this page,
    and a list of all the extracted links"""

    res = urlfetch.fetch(url)

    if res.status_code != 200:
        return None

    pprint(res.content)

    links = list(extract_links(res.content))

    pprint("Links contained in {}: ".format(url))
    pprint(links)

    return (PageNode(id, url, parent=parent), links)



