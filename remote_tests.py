import unittest

import requests

BASE_URL = 'https://gammacrawler.appspot.com/'

class RemoteTests(unittest.TestCase):

    def test_dummy_post(self):
        res = requests.post(BASE_URL + 'crawler')
        dummy_data = res.json()

        self.assertIn('status', dummy_data)
        self.assertIn('job_id', dummy_data)
        self.assertIn('root', dummy_data)
        self.assertIn('id', dummy_data['root'])
        self.assertEquals('www.google.com', dummy_data['root']['url'])
        self.assertIsNone(dummy_data['root']['parent'])

    def test_dummy_get(self):
        res = requests.get(BASE_URL + 'crawler/2')
        dummy_data = res.json()

        self.assertIn('finished', dummy_data)
        self.assertTrue(dummy_data['finished'])
        self.assertIn('new_pages', dummy_data)
        self.assertEqual(2, len(dummy_data['new_pages']))