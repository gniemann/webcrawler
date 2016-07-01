from pprint import pprint
import re
import random

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
"""
Explanation of regex:
<a [^>]*href=['"]?(?P<link>(https?://)?([a-z0-9\-]+\.){1,2}[a-z0-9]+(?<!\.html)((\?|/)[^'" ]*)?)['" ]

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

def get_host(url):
    """Extracts and returns just the service + host from url"""
    return host_regex.match(url).group()

def extract_links(page):
    return [match.group('link') for match in link_regex.finditer(page)]

def get_page(url, id, end_phrase=None, parent=None):
    """Retrieves the page pointed to by URL, extracts the links, and returns a tuple of a PageNode of this page,
    and a list of all the extracted links"""

    try:
        res = urlfetch.fetch(url)
    except:
        return None, None, None

    if res.status_code != 200:
        return None, None, None

    # discard links to the same host
    host = get_host(url)
    links = [link for link in extract_links(res.content) if not link.startswith(host)]

    pprint("Links contained in {}: ".format(url))
    pprint(links)

    if end_phrase and res.content.find(end_phrase) != -1:
        print "End phrase find!"
        phrase_found = True
    else:
        phrase_found = False

    return (PageNode(id, url, parent=parent, favicon=get_favicon(url)), links, phrase_found)

def get_favicon(url):
    """Attempts to get the site's favicon. If successful, returns the URL. On failure, returns None"""
    # use a regex to get the host
    match = host_regex.match(url)

    favicon_url = get_host(url) + '/favicon.ico'

    if urlfetch.fetch(favicon_url).status_code == 200:
        return favicon_url
    else:
        return None

def start_crawler(url, search_type, max_depth=3, end_phrase=None):
    """Starts a crawler job. On success, returns a 2-tuple of the root node and the job ID
    On failure, returns None"""

    #Ensure that our link starts with http
    if not url.startswith('http'):
        url = 'http://' + url

    # First get the root page. This validates that the URL is valid, so we can start and return something useful
    root, links, _ = get_page(url, 0)

    if search_type == 'DFS':
        crawler = depth_first_crawl
    else:
        crawler = bredth_first_crawl

    for node in crawler(links, max_depth, end_phrase):
        pprint(node.jsonify())

    return root, 2

def depth_first_crawl(starting_links, max_depth, end_phrase=None, parent_id=0):
    """Generator function which yields successive nodes in a depth first style
    Begins with a randomly selected link from links"""
    links = list(starting_links)
    cur_id = parent_id + 1
    cur_parent = parent_id

    for i in range(max_depth):
        print "At depth {}".format(i + 1)
        # if there are no links here, return
        if len(links) == 0:
            return

        # get a random link to follow
        link = random.choice(links)
        node, links, phrase_found = get_page(link, cur_id, end_phrase, cur_parent)

        yield node

        if phrase_found:
            return

def bredth_first_crawl(starting_links, max_depth, end_phrase=None, parent_id=0):
    """Generator function which yields successive nodes in a bredth first style"""
