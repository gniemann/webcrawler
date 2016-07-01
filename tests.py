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
    def test_dummy_post(self):
        submit_data = {
            'start_page': 'www.google.com',
            'depth': 3,
            'end_phrase': 'Larry Hotdogs',
            'search_type': 'BFS'
        }

        res = self.app.post('/crawler', data=submit_data)
        self.assertEqual(200, res.status_code)

        dummy_data = json.loads(res.data)

        self.assertIn('status', dummy_data)
        self.assertIn('root', dummy_data)
        self.assertIn('job_id', dummy_data)
        self.assertIn('id', dummy_data['root'])
        self.assertEquals('www.google.com', dummy_data['root']['url'])
        self.assertIsNone(dummy_data['root']['parent'])

    def test_post_error_no_start_page(self):
        submit_data = {
            'depth': 3,
            'end_phrase': 'Hotdogs',
            'search_type': 'BFS'
        }
        res = self.app.post('/crawler', data=submit_data)
        self.assertEqual(500, res.status_code, "Successful POST without required start_page")

    def test_post_error_wrong_search_type(self):
        submit_data = {
            'start_page': 'www.slashdot.org',
            'end_phrase': 'Hotdogs',
            'depth': 3,
            'search_type': 'whatevah'
        }
        res = self.app.post('/crawler', data=submit_data)
        self.assertEqual(500, res.status_code, "Successful POST with invalid search phrase")

    def _test_post_error_invalid_url(self):
        submit_data = {
            'start_page': 'Jupiter',
            'depth': 3,
            'end_phrase': 'Larry Hotdogs',
            'search_type': 'BFS'
        }
        res = self.app.post('/crawler', data=submit_data)
        self.assertEqual(500, res.status_code, 'Successful POST with invalid URL')

    def test_without_depth(self):
        submit_data = {
            'start_page': 'www.google.com',
            'end_phrase': 'Larry Hotdogs',
            'search_type': 'BFS'
        }
        res = self.app.post('/crawler', data=submit_data)
        self.assertEqual(200, res.status_code)

        return_data = json.loads(res.data)
        self.assertEqual(return_data['root']['url'], submit_data['start_page'])

    def test_dummy_get(self):
        res = self.app.get('/crawler/1')
        dummy_data = json.loads(res.data)

        self.assertIn('finished', dummy_data)
        self.assertTrue(dummy_data['finished'])
        self.assertIn('new_pages', dummy_data)
        self.assertEqual(2, len(dummy_data['new_pages']))

class TestGetPage(TestBase):
    def test_get_page(self):
        submit_data = {
            'start_page': 'https://www.google.com',
            'search_type': 'BFS'
        }
        res = self.app.post('/crawler', data=submit_data)
        self.assertEqual(200, res.status_code)

        return_data = json.loads(res.data)
        pprint(return_data)

        self.assertEqual(submit_data['start_page'], return_data['root']['url'])
