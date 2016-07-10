import logging
from pprint import pprint
import time
import unittest

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

start = time.time()

def logging_output(job_id, nodes):
    print "Time elapsed: {} seconds".format(time.time() - start)
    for node in nodes:
        if isinstance(node, crawler.TerminationSentinal):
            print "Finished!"
        else:
            pprint(node.jsonify())

class CrawlerTest(unittest.TestCase):
    def test_bredth_first(self):
        crawl = crawler.BredthFirstCrawl('1', logging_output, 2, 'terms of service')
        crawl(['www.google.com'])
