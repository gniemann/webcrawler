import logging
from pprint import pprint
import unittest

from guppy import hpy
import requests

import crawler
import page

logging.basicConfig(level=logging.INFO)

def retrive_url(url):
    res = requests.get(url)

    if res.status_code != 200:
        return None

    return res

page.retrieve_url = retrive_url
h = hpy()

def logging_output(job_id, nodes):
    for node in nodes:
        if not isinstance(node, crawler.TerminationSentinal):
            pprint(node.jsonify())
    pprint(h.heap())

class CrawlerTest(unittest.TestCase):
    def test_bredth_first(self):
        crawl = crawler.BredthFirstCrawl('1', logging_output, 2)
        crawl(['www.slashdot.org'])
