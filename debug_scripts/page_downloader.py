import pprint

import HTTPtentacle.HTML_Downloader

if __name__ == "__main__":
    page_link = "https://baike.baidu.com/item/%E8%8C%B6/6227"

    html = HTTPtentacle.HTML_Downloader.HTMLDownloader.get_page_content(page_link)
    pprint.pprint(html)
    with open('./debug_html/webpage.html', 'w', encoding='utf-8') as file:
        file.write(html['html'])
