import json
import pprint
import urllib

import bs4
import re as regex
import requests
from urllib.parse import quote


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

    def load_content(self, html_text: str):
        """装填百度百科页面的内容，以供分析"""
        self.content = html_text
        self.soup = bs4.BeautifulSoup(self.content, "html.parser")
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

    @staticmethod
    def remove_hyperlink(soup_tag):
        # 禁用所有超链
        href_list = soup_tag.find_all("a", href=True)
        if href_list is not None:
            for tag in href_list:
                tag.unwrap()

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
            if isinstance(child, bs4.NavigableString) \
                    and child.parent.name != "sup":  # 筛选不在引用连接外的字符串
                summary += str(child).strip()
        return summary

    def get_sharecount_data(self) -> dict:
        """
        获取转发和点赞数（ajax异步内容，需要请求服务器）
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

    def get_item_basic_info(self) -> dict:
        """以字典的形式获取词条的定义属性"""
        # 切出属性栏区块
        info_part = self.soup.find('div', class_='basic-info')
        self.remove_ref(info_part)  # 切除参考文献角标
        self.remove_hyperlink(info_part)  # 移除超链标记
        # 分列操作
        columns = [info_part.find('dl', class_="basicInfo-left"), info_part.find('dl', class_="basicInfo-right")]
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
                        keymap[key] = regex.sub(r'[\xa0\n]', ' ', value.strip())  # 输出前一条目
                        key = ''.join(current_tag.text.split())
                        value = ''  # 清空内容
                    current_tag = current_tag.next_sibling
        keymap[key] = regex.sub(r'[\xa0 \n]', ' ', value.strip())  # 输出缓存
        keymap.pop('')  # 剔除初始化项
        return keymap

    def get_item_relation_table(self, soup=None):
        """
        获取百科词条页面下方相关内容表格（ajax异步内容，需要请求服务器）
        :raise Exception 请求失败
        """
        if soup is None:
            soup = self.soup
        table_list = soup.find_all(class_="rs-container")
        if table_list is None:
            return None
        else:
            # 总输出
            output = list()
            for table in table_list:
                table_id = table['id'].split('-')[3]
                root_url = "https://baike.baidu.com/guanxi/jsondata"  # 获取内容的地址
                get_appendix = '?action={action}&args={args}'  # get传参模版
                action_str = "getViewLemmaData"  # 固定参数
                args = [0, 8, {"fentryTableId": table_id}, False]  # 在这里传入条目表的id

                # 将参数内容转为url转义编码插入
                requset_url = (root_url + get_appendix.format(action=quote(action_str), args=quote(str(args))))
                try:
                    # 获取表格json
                    req = urllib.request.Request(requset_url, headers=self.headers)
                    response = urllib.request.urlopen(req, timeout=5)
                    if response.getcode() != 200:
                        raise Exception("connection error on relation table fetching")
                except Exception as e:
                    # 连接中断：
                    raise e  # 目前单纯传出异常
                # json直接取值，获得表格区的HTML和总标题
                json_data = json.load(response)
                html_text = regex.sub(r'(\r\n)', "", json_data['html'])
                main_title = json_data["title"]
                # 初始化输出缓存
                result = dict()
                result['name'] = main_title
                value_list = []
                # 解析html
                relation_soup = bs4.BeautifulSoup(html_text, features='html.parser')
                r_unit_list = relation_soup.find_all(class_='relation-unit', recursive=False)
                if relation_soup.find('h3') is None:
                    # 分块
                    for unit in r_unit_list:
                        if unit.name == 'table':
                            # 移交递归函数处理表格
                            value_list.append(self._parse_table_recursive(unit))
                        if unit.name == 'div':
                            # 直接提取
                            rows = unit.table.find_all('span', class_="entry-item")
                            for row in rows:
                                href = row.a['href']
                                value = ""
                                for string in row.stripped_strings:
                                    value += string
                                value_list.append((value, href))
                    result['content'] = value_list
                    output.append(result)
                else:
                    h3_name = ""
                    sublist = []
                    for unit in r_unit_list:
                        if unit.name == 'h3':
                            value_list.append({'name': h3_name, 'content': sublist})
                            h3_name = ''
                            for string in unit.stripped_strings:
                                h3_name += string
                            sublist = []
                        elif unit.name == 'div':
                            # 直接提取
                            rows = unit.table.find_all('span', class_="entry-item")
                            for row in rows:
                                href = row.a['href']
                                value = ""
                                for string in row.stripped_strings:
                                    value += string
                                sublist.append((value, href))
                    value_list.append({'name': h3_name, 'content': sublist})  # 清空缓存
                    value_list.pop(0)  # 去除占位
                    result['content'] = value_list
                    output.append(result)
            return output

    def _parse_table_recursive(self, main_tag):
        # 递归处理嵌套的表格内容
        result = dict()
        value_list = []
        title = main_tag.tr.th.text
        result['name'] = title
        operation_plat = main_tag.tr.td.table.tr
        while operation_plat is not None:
            if isinstance(operation_plat, bs4.NavigableString):
                operation_plat = operation_plat.next_sibling
                continue
            if operation_plat.td.table.get('class') is not None:
                rows = operation_plat.td.table.find_all('span', class_="entry-item")
                for row in rows:
                    href = row.a['href']
                    value = ""
                    for string in row.stripped_strings:
                        value += string
                    value_list.append((value, href))
            else:
                value_list.append(self._parse_table_recursive(operation_plat.td.table))
            operation_plat = operation_plat.next_sibling
        result['content'] = value_list
        return result


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
