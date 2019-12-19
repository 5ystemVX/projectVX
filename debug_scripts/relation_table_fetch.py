import json
import re
import urllib.request
import bs4
from urllib.parse import quote

# 获取百度百科关系表HTML
if __name__ == "__main__":
    header = {'Accept': '*/*',
              'Accept-Language': 'en-US,en;q=0.8',
              'Cache-Control': 'max-age=0',
              'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                            'Chrome/48.0.2564.116 Safari/537.36',
              'Connection': 'keep-alive',
              'Referer': 'http://www.baidu.com/'
              }

    url = "https://baike.baidu.com/guanxi/jsondata"

    get_appendix = '?action={action}&args={args}'
    args = [0, 8, {"fentryTableId": 40978}, False]
    action_str = "getViewLemmaData"
    requset_url = (url + get_appendix.format(
        args=quote(str(args)), action=action_str))

    print(requset_url)
    req = urllib.request.Request(requset_url, headers=header)
    response = urllib.request.urlopen(req, timeout=5)
    if response.getcode() != 200:
        print('error fetching')
    # json直接取值,先不解析table，直接把代码拿出来
    json_data = json.load(response)
    text = re.sub(r'\r\n', '', json_data['html'])
    print(json_data['title'])
    with open("debug_html/relation_table_test.html", 'w', encoding='utf-8') as file:
        file.write(text)
