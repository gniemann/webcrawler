import json
import unittest

from google.appengine.ext import testbed

from main import app

test_bed = testbed.Testbed()
test_bed.activate()

class Tests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['DEBUG'] = True
        self.app = app.test_client()


    def test_dummy_post(self):
        res = self.app.post('/crawler')
        dummy_data = json.loads(res.data)
        print res.headers

        self.assertIn('status', dummy_data)
        self.assertIn('root', dummy_data)
        self.assertIn('job_id', dummy_data)
        self.assertIn('id', dummy_data['root'])
        self.assertEquals('www.google.com', dummy_data['root']['url'])
        self.assertIsNone(dummy_data['root']['parent'])

    def test_dummy_get(self):
        res = self.app.get('/crawler/1')
        dummy_data = json.loads(res.data)
        self.assertIn('finished', dummy_data)
        self.assertTrue(dummy_data['finished'])
        self.assertIn('new_pages', dummy_data)
        self.assertEqual(2, len(dummy_data['new_pages']))

