from collections import Counter
from pprint import pprint
import unittest
import time

import requests

#BASE_URL = 'http://localhost:8080/'
BASE_URL = 'https://gammacrawler.appspot.com/'


class Tests(unittest.TestCase):
    def test_post(self):
        submit_data = {
            'start_page': 'www.google.com',
            'depth': 2,
            'end_phrase': 'Larry Hotdogs',
            'search_type': 'BFS'
        }

        res = requests.post(BASE_URL + 'crawler', data=submit_data)
        self.assertEqual(200, res.status_code)

        return_data = res.json()

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
        res = requests.post(BASE_URL + 'crawler', data=submit_data)
        self.assertIn('errors', res.json(), "Successful POST without required start_page")

    def test_post_error_wrong_search_type(self):
        submit_data = {
            'start_page': 'www.slashdot.org',
            'end_phrase': 'Hotdogs',
            'depth': 3,
            'search_type': 'whatevah'
        }
        res = requests.post(BASE_URL + 'crawler', data=submit_data)
        self.assertIn('errors', res.json(), "Successful POST with invalid search phrase")

    def test_post_error_invalid_url(self):
        submit_data = {
            'start_page': 'Jupiter',
            'depth': 3,
            'end_phrase': 'Larry Hotdogs',
            'search_type': 'BFS'
        }
        res = requests.post(BASE_URL + 'crawler', data=submit_data)
        self.assertIn('errors', res.json(), "Successful POST with invalid URL")

    def test_without_depth(self):
        submit_data = {
            'start_page': 'www.slashdot.org',
            'end_phrase': 'Larry Hotdogs',
            'search_type': 'BFS'
        }
        res = requests.post(BASE_URL + 'crawler', data=submit_data)
        return_data = res.json()

        self.assertNotIn('errors', return_data, "Unsuccessful POST without depth")

        self.assertIn(submit_data['start_page'], return_data['root']['url'])


class TestGetPage(unittest.TestCase):
    def get_future_results(self, job_id):
        nodes = []
        finished = False
        i = 1
        while not finished:
            time.sleep(2)

            res = requests.get(BASE_URL + 'crawler/{}'.format(job_id))

            new_nodes = res.json()

            print "New nodes in iteration {}".format(i)
            pprint(new_nodes)

            nodes.extend(new_nodes['new_nodes'])

            if new_nodes['finished']:
                print "Crawl complete!"
                finished = True

            i += 1

        return nodes

    def conduct_test(self, searcb_type):
        submit_data = {
            'start_page': 'https://www.slashdot.org',
            'search_type': searcb_type,
            'depth': 2
        }
        res = requests.post(BASE_URL + 'crawler', data=submit_data)
        self.assertEqual(200, res.status_code)

        return_data = res.json()
        pprint(return_data)

        self.assertEqual(submit_data['start_page'], return_data['root']['url'])

        nodes = []
        nodes.append(return_data['root'])

        nodes.extend(self.get_future_results(return_data['job_id']))

    def test_depth_first(self):
        print "Testing Depth First Crawl"

        self.conduct_test('DFS')

    def test_bredth_first(self):
        print "Testing Bredth First Crawl"

        self.conduct_test('BFS')
