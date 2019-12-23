import copy
import json
import pprint
import time
import urllib.request

import bs4
import re as regex
import requests
from urllib.parse import quote


# noinspection PyMethodMayBeStatic
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
        self.html = None
        self.soup = None
        self.url_prefix = "https://baike.baidu.com"
        self.baidu_error_url = "https://baike.baidu.com/error.html"

    def __check_404_error(self, url):
        if regex.match(self.baidu_error_url, url) is None:
            return False
        else:
            return True

    def load_content(self, html_soup) -> None:
        """
        装填百度百科页面的内容，以供分析
        :param html_soup: html字符串，或者soup对象
        :return: None
        """
        if isinstance(html_soup, str):
            self.html = html_soup
            self.soup = bs4.BeautifulSoup(self.html, "html.parser")
        elif isinstance(html_soup, bs4.BeautifulSoup) or isinstance(html_soup, bs4.Tag):
            self.soup = html_soup
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

    def get_main_hyperlink(self):
        """
        获取正文里所有指向其他词条的超链接
        :return: 2元素元祖列表
        """
        result = []
        main_tag = self.soup.find('div', class_="main-content")
        href_list = main_tag.find_all('a', href=regex.compile(r"^(/item/)|(/view/).*"))
        if href_list is not None:
            for href in href_list:
                result.append((href.get_text(), href['href']))
        else:
            return None
        return result

    def get_item_title(self) -> str:
        """
         获取词条标题和副标题的拼接（如果有)
        :return: str
        """
        # 切出标题部分
        title_part = self.soup.find(attrs={"class": "lemmaWgt-lemmaTitle-title"})
        # 截取标题
        title = title_part.find(name='h1').string
        # 截取副标题（如果有）
        if title_part.find(name="h2") is not None:
            title += title_part.find(name='h2').string
        return title

    def get_item_summary(self) -> str or None:
        """
        获取词条的概述区块纯文本
        :return str:
        """
        # 切割主页概述区块
        summary_part = self.soup.find(attrs={"class": "lemma-summary"})
        if summary_part is None:
            return None
        # 拼接完整概述
        summary = ""
        for child in summary_part.descendants:  # 递归查找所有子元素
            if isinstance(child, bs4.NavigableString) \
                    and child.parent.name != "sup":  # 筛选不在引用连接外的字符串
                summary += str(child).strip()
        return summary

    def get_item_basic_info(self) -> dict or None:
        """
        以字典的形式获取词条的定义属性
        :return: dict
        """
        # 切出属性栏区块
        info_part = self.soup.find('div', class_='basic-info')
        if info_part is None:
            return None
        info_part = copy.copy(info_part)  # 不改动原始数据
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

    def get_item_reference(self) -> list or None:
        """
        获取词条参考资料区块
        :return: list[tuple(参考资料文字内容,链接),None 如果没有参考资料区域
        """
        output = []
        # 切出参考资料区块
        ref_block = self.soup.find('dl', class_="lemma-reference")
        if ref_block is None:
            return None
        # 删除序号
        for item in ref_block.find_all('span', class_="index"):
            item.decompose()
        for ref_row in ref_block.find_all("li", class_="reference-item"):
            text = "".join(ref_row.stripped_strings)
            if ref_row.find('a', class_="text") is not None:
                output.append((text, ref_row.find('a', class_="text")['href']))
            else:
                output.append((text, None))
        return output

    def get_share_like_count(self) -> dict or None:
        """
        获取转发、点赞数（ajax异步内容，需要请求2次服务器）

        返回  dict ｛share,like,review} 格式值
             None 如果404
        :raises Exception 连接失败
        """
        # 获取 Lemma id
        lemma_id_div = self.soup.find('div', class_='lemmaWgt-promotion-rightPreciseAd')
        lemma_id = regex.findall('data-lemmaid="(.*)" ', str(lemma_id_div))

        # 拼接查询URL
        share_like_url = "https://baike.baidu.com/api/wikiui/sharecounter?lemmaId={}".format(lemma_id[0])
        try:
            # 请求服务器返回值
            req = urllib.request.Request(share_like_url, headers=self.headers)
            response = urllib.request.urlopen(req, timeout=5)
            if self.__check_404_error(response.url):
                return None
            # json直接取值
            json_data = json.load(response)
        except Exception as e:
            raise e
        like_count = json_data['likeCount'] if json_data.get('likeCount') is not None else 0
        share_count = json_data['shareCount'] if json_data.get('shareCount') is not None else 0

        return {"share": share_count, "like": like_count}

    def get_preview_count(self, id_enc: str):
        """
        获取浏览数（ajax异步内容，需要请求2次服务器）
        :param id_enc: 页面id的hash（未推出hash方式，需要直接提取的字符串）
        :raises Exception: 连接失败
        :return int or None:
        """
        if isinstance(id_enc, dict):
            id_enc = id_enc.get('newLemmaIdEnc')
        if id_enc is None:
            return None

        review_url = "http://baike.baidu.com/api/lemmapv?id={}&r={}".format(id_enc, str(int(time.time())))
        try:
            # 请求服务器返回值
            req = urllib.request.Request(review_url, headers=self.headers)
            response = urllib.request.urlopen(req, timeout=5)
            if self.__check_404_error(response.url):
                return None
            # json直接取值
            json_data = json.load(response)
        except Exception as e:
            raise e
        review_count = json_data['pv'] if json_data.get('pv') is not None else 0
        return review_count

    def get_item_tag(self):
        # 词条标签：不一定每个词条都有，需要筛选有的再查
        tag_node = self.soup.find('div', id="open-tag")
        if tag_node is None:
            return None
        else:
            result_list = []
            tags = tag_node.find_all('span')
            for tag in tags:
                result_list.append(''.join(tag.stripped_strings))
        return result_list

    def get_main_content(self):
        """
        获取百度百科页面正文的文本内容，保持目录结构(暂不处理内嵌table等格式）
        :return: 嵌套的list,每个list[0]元素为该段落标题
        """
        # 正文部分：
        main_copy = copy.copy(self.soup.find('div', class_="main-content"))
        # 切除图片说明
        temp = main_copy.find_all('span', class_="description")
        title = None
        if temp is not None:
            for description in temp:
                description.decompose()
        # 切除标题前缀词
        temp = main_copy.find_all('span', class_="title-prefix")
        if temp is not None:
            title = temp[0].text
            for item in temp:
                item.decompose()
        # 内容游标
        content_cursor = main_copy.find('div', class_="configModuleBanner")

        # 标题栈，预先压入一层壳子
        title_stack = [[title]]
        # 内容缓存
        content_buffer = ''

        while content_cursor is not None:
            # 顺序遍历
            content_cursor = content_cursor.next_sibling
            # 筛掉字符串
            if not isinstance(content_cursor, bs4.Tag):
                continue
            # 表格没有统一class特征，得提前识别
            if content_cursor.name == "table":
                content_buffer += "".join(content_cursor.stripped_strings) + "  "
            if content_cursor.get('class') is None:
                continue
            # 筛掉超链跳转标记
            if 'anchor-list' in content_cursor['class']:
                continue
            # 文本段
            if 'para' in content_cursor['class'] or 'para-list' in content_cursor['class']:
                content_buffer += "".join(content_cursor.stripped_strings) + "  "
            # 标题段
            elif 'para-title' in content_cursor['class']:
                # 文本内容打包进当前最小标题
                if content_buffer != '':
                    title_stack[len(title_stack) - 1].append(content_buffer.strip())
                    content_buffer = ''

                if "level-2" in content_cursor['class']:
                    if len(title_stack) > 1:
                        while len(title_stack) > 1:
                            content = title_stack.pop()
                            title_stack[len(title_stack) - 1].append(content)
                    title = content_cursor.find('h2').text
                    title_stack.append([title])
                elif "level-3" in content_cursor['class']:
                    if len(title_stack) > 2:
                        while len(title_stack) > 2:
                            content = title_stack.pop()
                            title_stack[len(title_stack) - 1].append(content)
                    title = content_cursor.find('h3').text
                    title_stack.append([title])
        # 收尾，输出栈内剩余内容
        if content_buffer != '':
            title_stack[len(title_stack) - 1].append(content_buffer.strip())
        while len(title_stack) > 1:
            while len(title_stack) > 1:
                content = title_stack.pop()
                title_stack[len(title_stack) - 1].append(content)

        pprint.pprint(title_stack[0])

    def get_item_relation_table(self, soup=None):
        """
        获取百科词条页面下方相关内容表格（ajax异步内容，需要请求服务器）
        :param soup: 词条页面解析的BeautifulSoup对象
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
                output.append(self.parse_single_relation_table(table_id))
        return output

    def parse_single_relation_table(self, rt_id: int):
        """
        解析单个相关内容表格（ajax异步内容，需要请求服务器）
        :param rt_id: 表格id
        :raise Exception 请求失败
        """
        root_url = "https://baike.baidu.com/guanxi/jsondata"  # 获取内容的地址
        get_appendix = '?action={action}&args={args}'  # get传参模版
        action_str = "getViewLemmaData"  # 固定参数
        args = [0, 8, {"fentryTableId": rt_id}, False]  # 在这里传入条目表的id

        # 将参数内容转为url转义编码插入
        request_url = (root_url + get_appendix.format(action=quote(action_str), args=quote(str(args))))
        try:
            # 获取表格json
            req = urllib.request.Request(request_url, headers=self.headers)
            response = urllib.request.urlopen(req, timeout=5)
            if self.__check_404_error(response.url):
                return None
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
        result_single_table = dict()
        # 加入表名
        result_single_table['#head_name#'] = main_title
        result_single_table['#head_link#'] = None
        result_single_table['#table_id#'] = rt_id
        # 解析Html
        relation_soup = bs4.BeautifulSoup(html_text, features='html.parser')
        r_unit_list = relation_soup.find_all(class_='relation-unit', recursive=False)
        # h3,div,table混合格式
        h3_name = None
        h3_buffer = {}
        for unit in r_unit_list:  # 切分为最大单个元素，分别处理
            if unit.name == 'h3':  # 以h3为分界，按顺序打包
                if h3_name not in (None, ''):
                    result_single_table[h3_name] = h3_buffer
                h3_name = ''.join(unit.stripped_strings)
                h3_buffer.clear()
            if unit.name == 'table':
                # 移交递归函数处理table
                item = self.__parse_table_recursive(unit)
                if h3_name is not None:
                    if item.get('#head_name#') is None:
                        h3_buffer = dict(h3_buffer, **item)
                    else:
                        h3_buffer[item.get('#head_name#')] = item
                else:
                    if item.get('#head_name#') is None:
                        result_single_table = dict(result_single_table, **item)
                    else:
                        result_single_table[item.get('#head_name#')] = item
            if unit.name == "div":
                # 提取 div
                div_content = self.__parse_div_(unit)
                if h3_name is not None:
                    h3_buffer = dict(h3_buffer, **div_content)
                else:
                    result_single_table = dict(result_single_table, **div_content)
        if h3_name is not None:  # 输出缓存
            h3_buffer['#head_name#'] = None
            result_single_table[h3_name] = h3_buffer  # 输出缓存
        return result_single_table

    def __parse_table_recursive(self, table_tag):
        """
        递归处理表格tag
        :param table_tag:
        :return:
        """
        if table_tag.tr.find('td', recursive=False) is None:
            # 表格由th存储信息
            return self.__parse_div_(table_tag)
        else:
            if table_tag.get('class') is not None and table_tag.get('class')[0] == 'tb-entries':
                # 叶table节点，直接提取信息
                return self.__parse_div_(table_tag)
            else:
                content = {}
                # 中间节点,整理下方传来的信息
                # 寻找下一级标签(table或div)
                for table_row in table_tag.find_all('tr', recursive=False):
                    child_tag = table_row.td.contents[0]
                    if child_tag.name == "table":
                        temp = self.__parse_table_recursive(child_tag)
                    else:
                        temp = self.__parse_div_(child_tag)
                    # @temp: 下一层的内容
                    if temp.get('#head_name#') in (None, ''):  # 下一级是结构中继节点，不计入内容层级
                        # 拆包，把内容追加在该层内容里
                        content = dict(content, **temp)
                    else:
                        # 提取下层词典的表头名作为key，存成一项
                        content[temp.get('#head_name#')] = temp
                if table_tag.tr.find('th', recursive=False) is not None:  # 自己不是结构中继节点
                    title = table_tag.tr.th.text  # 提取标题
                    content['#head_name#'] = title
                    href = table_tag.tr.th.find('a', href=True)  # 查找标题链接
                    if href is not None:
                        content['#head_link#'] = href['href']  # 存储链接
                    else:
                        content['#head_link#'] = None
                return content

    def __parse_div_(self, div_tag):
        # 处理一般div内容
        # 直接提取
        div_content = dict()
        rows = div_tag.find_all('span', class_="entry-item")
        if rows is not None:
            for row in rows:
                href = row.a['href'] if row.find('a') is not None else None
                value = "".join(row.stripped_strings)
                div_content[value] = href
        return div_content
