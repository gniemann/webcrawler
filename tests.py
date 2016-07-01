import json
import unittest
from pprint import pprint

from google.appengine.ext import testbed

from main import app

test_bed = testbed.Testbed()
test_bed.activate()
test_bed.init_urlfetch_stub()

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

    def test_dummy_get(self):
        res = self.app.get('/crawler/1')
        dummy_data = json.loads(res.data)

        self.assertIn('finished', dummy_data)
        self.assertTrue(dummy_data['finished'])
        self.assertIn('new_pages', dummy_data)
        self.assertEqual(2, len(dummy_data['new_pages']))

class TestGetPage(TestBase):
    def _test_depth_first(self):
        submit_data = {
            'start_page': 'https://www.google.com',
            'search_type': 'DFS'
        }
        res = self.app.post('/crawler', data=submit_data)
        self.assertEqual(200, res.status_code)

        return_data = json.loads(res.data)
        pprint(return_data)

        self.assertEqual(submit_data['start_page'], return_data['root']['url'])

    def test_end_phrase(self):
        submit_data = {
            'start_page': 'https://www.google.com',
            'search_type': 'DFS',
            'end_phrase': 'Google'
        }

        res = self.app.post('/crawler', data=submit_data)
