import json
import unittest
from pprint import pprint
import time

from google.appengine.ext import testbed, deferred

from crawler import app

test_bed = testbed.Testbed()
test_bed.activate()
test_bed.init_urlfetch_stub()
test_bed.init_taskqueue_stub()
test_bed.init_memcache_stub()

class TestBase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['DEBUG'] = True
        self.app = app.test_client()

class Tests(TestBase):
    def test_post(self):
        submit_data = {
            'start_page': 'www.google.com',
            'depth': 3,
            'end_phrase': 'Larry Hotdogs',
            'search_type': 'BFS'
        }

        res = self.app.post('/crawler', data=submit_data)
        self.assertEqual(200, res.status_code)

        return_data = json.loads(res.data)

        self.assertIn('status', return_data)
        self.assertIn('root', return_data)
        self.assertIn('job_id', return_data)
        self.assertIn('id', return_data['root'])
        self.assertIn('www.google.com', return_data['root']['url'])
        self.assertIsNone(return_data['root']['parent'])
        self.assertEqual(return_data['root']['favicon'], 'http://www.google.com/favicon.ico')

    def test_post_error_no_start_page(self):
        submit_data = {
            'depth': 3,
            'end_phrase': 'Hotdogs',
            'search_type': 'BFS'
        }
        res = self.app.post('/crawler', data=submit_data)
        self.assertIn('errors', res.data, "Successful POST without required start_page")

    def test_post_error_wrong_search_type(self):
        submit_data = {
            'start_page': 'www.slashdot.org',
            'end_phrase': 'Hotdogs',
            'depth': 3,
            'search_type': 'whatevah'
        }
        res = self.app.post('/crawler', data=submit_data)
        self.assertIn('errors', res.data, "Successful POST with invalid search phrase")

    def _test_post_error_invalid_url(self):
        submit_data = {
            'start_page': 'Jupiter',
            'depth': 3,
            'end_phrase': 'Larry Hotdogs',
            'search_type': 'BFS'
        }
        res = self.app.post('/crawler', data=submit_data)
        self.assertIn('errors', res.data, "Successful POST with invalid URL")

    def test_without_depth(self):
        submit_data = {
            'start_page': 'www.slashdot.org',
            'end_phrase': 'Larry Hotdogs',
            'search_type': 'BFS'
        }
        res = self.app.post('/crawler', data=submit_data)
        self.assertNotIn('errors', res.data, "Unsuccessful POST without depth")

        return_data = json.loads(res.data)
        self.assertIn(submit_data['start_page'], return_data['root']['url'])

class TestGetPage(TestBase):
    def get_future_results(self, job_id):
        for i in range(5):
            time.sleep(2)

            res = self.app.get('crawler/{}'.format(job_id))

            new_nodes = json.loads(res.data)

            print "New nodes in iteration {}".format(i + 1)
            pprint(new_nodes)

            if new_nodes['finished']:
                print "Crawl complete!"
                break


    def _test_depth_first(self):
        submit_data = {
            'start_page': 'https://www.google.com',
            'search_type': 'DFS'
        }
        res = self.app.post('crawler', data=submit_data)
        self.assertEqual(200, res.status_code)

        return_data = json.loads(res.data)
        pprint(return_data)

        self.assertEqual(submit_data['start_page'], return_data['root']['url'])

        self.get_future_results(return_data['job_id'])


    def test_bredth_first(self):
        submit_data = {
            'start_page': 'https://www.google.com',
            'search_type': 'BFS',
            'depth': 1
        }

        res = self.app.post('crawler', data=submit_data)
        self.assertEqual(200, res.status_code)

        return_data = json.loads(res.data)

        self.get_future_results(return_data['job_id'])
