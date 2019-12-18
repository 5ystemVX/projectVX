import json

from bs4 import BeautifulSoup
from bs4 import NavigableString
import re as regex
import requests
import html


class BaiduBaikeParser(object):

    def __init__(self):
        self.headers = {'Accept': '*/*',
                        'Accept-Language': 'en-US,en;q=0.8',
                        'Cache-Control': 'max-age=0',
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                      'Chrome/48.0.2564.116 Safari/537.36',
                        'Connection': 'keep-alive',
                        'Referer': 'http://www.baidu.com/'
                        }
        self.content = None
        self.soup = None
        self.url_prefix = "https://baike.baidu.com"
        pass

    def set_content(self, html_text: str):
        """装填百度百科页面的内容，以供分析"""
        self.content = html_text
        self.soup = BeautifulSoup(self.content, "html.parser")
        self.remove_ref(self.soup)

    @staticmethod
    def remove_ref(soup_tag):
        # 删除所有参考引用的角标
        sup_list = soup_tag.find_all("sup", class_="sup--normal")
        if sup_list is not None:
            for sup in sup_list:
                sup.decompose()
            for anchor in soup_tag.find_all("a", class_="sup-anchor"):
                anchor.decompose()

    def get_item_title(self) -> str:
        """ 获取词条标题和副标题的拼接（如果有）"""
        # 切出标题部分
        title_part = self.soup.find(attrs={"class": "lemmaWgt-lemmaTitle-title"})
        # 截取标题
        title = title_part.find(name='h1').string
        # 截取副标题（如果有）
        if title_part.find(name="h2") is not None:
            title += title_part.find(name='h2').string
        return title

    def get_item_summary(self) -> str:
        """ 获取词条的概述区块纯文本"""
        # 切割主页概述区块
        summary_part = self.soup.find(attrs={"class": "lemma-summary"})
        # 拼接完整概述
        summary = ""
        for child in summary_part.descendants:  # 递归查找所有子元素
            if isinstance(child, NavigableString) \
                    and child.parent.name != "sup":  # 筛选不在引用连接外的字符串
                summary += str(child).strip()
        return summary

    # 获取转发和点赞数(需要访问百科服务器）
    def get_sharecount_data(self) -> dict:
        """
        获取转发和点赞数(需要访问百科服务器）
        :raises e 连接失败
        """
        # 获取 Lemma id
        lemma_id_div = self.soup.find('div', class_='lemmaWgt-promotion-rightPreciseAd')
        lemma_id = regex.findall('data-lemmaid="(.*)" ', str(lemma_id_div))
        # 拼接查询URL
        state_url = 'https://baike.baidu.com/api/wikiui/sharecounter?lemmaId={}'.format(lemma_id[0])
        try:
            # 请求服务器返回值
            response = requests.get(state_url, headers=self.headers, timeout=5)
            response.raise_for_status()
            # json直接取值
            json_data = json.loads(response.text)
        except Exception as e:
            raise e
        like_count = json_data['likeCount'] if json_data['likeCount'] is not None else 0
        share_count = json_data['shareCount'] if json_data['shareCount'] is not None else 0
        return {"share": share_count, "like": like_count}

    def get_item_def_info(self):
        # 切出属性栏区块
        info_part = self.soup.find('div', class_='basic-info')
        self.remove_ref(info_part)  # 切除参考文献角标
        columns = []
        columns.append(info_part.find('dl', class_="basicInfo-left"))  # 左边一列
        columns.append(info_part.find('dl', class_="basicInfo-right"))  # 右边一列
        keymap = dict()
        key = ''
        value = ''
        for column in columns:  # 两列操作方式相同
            if column is not None:
                current_tag = column.contents[0]
                while current_tag is not None:
                    if current_tag.name == "dd":
                        for string in current_tag.strings:
                            value += regex.sub(r"\\'", "'", string)
                    elif current_tag.name == "dt":  # 新条目头
                        keymap[key] = regex.sub(r'[\xa0 \n]', ' ', value.strip())  # 输出前一条目
                        key = ''.join(current_tag.text.split())
                        value = ''  # 清空内容
                    current_tag = current_tag.next_sibling
        keymap[key] = value.strip()  # 输出缓存
        keymap.pop('')  # 剔除初始化项
        return keymap


if __name__ == "__main__":
    with open(r'E:\[Study]\PycharmProject\NetHook\123.html', 'r', encoding="utf-8") as file:
        content = file.read()
    parser = BaiduBaikeParser()
    parser.set_content(content)
    print("title-------------")
    print(parser.get_item_title())
    print("summary-------------")
    print(parser.get_item_summary())
    print("share,like-------------")
    print(parser.get_sharecount_data())
    print("basic-info----------------")
    print(parser.get_item_def_info())
