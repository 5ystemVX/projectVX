import random
import time
import unittest

from DataAnalyzing.BaiduBaike_Parser import BaiduBaikeParser
from HTTPtentacle.HTML_Downloader import HTMLDownloader
import pprint
import re
from urllib.parse import quote
import urllib.request
import json


class MyTestCase(unittest.TestCase):
    def test_something(self):

        header = {'Accept': '*/*',
                  'Accept-Language': 'en-US,en;q=0.8',
                  'Cache-Control': 'max-age=0',
                  'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/48.0.2564.116 Safari/537.36',
                  'Connection': 'keep-alive',
                  'Referer': 'http://www.baidu.com/'
                  }

        content = HTMLDownloader.get_page_content('https://baike.baidu.com/item/%E9%92%9B/499070', header)
        parser = BaiduBaikeParser()
        parser.load_content(content[0])
        # followings are proven:
        # print("title-------------")
        # print(parser.get_item_title())
        # print("summary-------------")
        # print(parser.get_item_summary())
        # print("share,like-------------")
        # print(parser.get_sharecount_data())
        # print("basic-info----------------")
        # print(parser.get_item_basic_info())
        # print("relation-table------------")
        # tables = parser.get_item_relation_table()
        # pprint.pprint(tables)
        # print('reference------------')
        # pprint.pprint(parser.get_item_reference())

    def test_relation_table_parsing(self):
        r_table_ids = [3985]
        for i in range(10):
            r_table_ids.append(random.randint(1000, 4000))
        for r_id in r_table_ids:
            parser = BaiduBaikeParser()
            url = "https://baike.baidu.com/guanxi/jsondata"

            get_appendix = '?action={action}&args={args}'
            args = [0, 8, {"fentryTableId": r_id}, False]
            action_str = "getViewLemmaData"
            requset_url = (url + get_appendix.format(args=quote(str(args)), action=action_str))
            print('------------------------ id = {} -----------------------'.format(r_id))
            print(requset_url)
            result_dict = parser.parse_single_relation_table(r_id)
            pprint.pprint(result_dict)
            time.sleep(0.5)

            # 结果demo
            '''
            ------------------------ id = 38410 -----------------------
            https://baike.baidu.com/guanxi/jsondata?action=getViewLemmaData&args=%5B0%2C%208%2C%20%7B%27fentryTableId%27%3A%2038410%7D%2C%20False%5D
            cost: 0.0638275146484375 sec(s)
            {'#head_link#': None,
             '#head_name#': '中国六大茶类',
             '乌龙茶': {'#head_link#': 'http://baike.baidu.com/subview/6154/5060874.htm',
                       '#head_name#': '乌龙茶',
                       .....................
            '''


if __name__ == '__main__':
    unittest.main()
