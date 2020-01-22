import os
import re
import time

import HTTPtentacle.HTML_Downloader
import HTTPtentacle.Mysql_connector


class SpiderSlave(object):
    def __init__(self, step_length=100, log_dir=None):
        self.timestamp = time.time()  # 时间戳，计时统计用
        self.crawled_page_count = 0  # 总爬取计数
        self.partial_crawl_count = 0  # 部分爬取计数
        self.error_404_count = 0  # 遇到不存在的网页计数
        self.partial_404_count = 0
        self.buffer_list = []  # 爬到的内容缓存
        self.connect_error_list = []  # 连接失败url记录缓存
        self.dbconn = HTTPtentacle.Mysql_connector.MysqlConnector()  # sql接口
        self.crawl_step_length = 100 if step_length <= 0 else step_length  # 爬取步长
        self.logfile_dir = "spider.log" if log_dir is None else log_dir  # log位置
        self.log_buffer = ""  # log内容缓存

    def connect_sql(self, host, user, pwd, dbname):
        # self.dbconn.toggle_debug(True)
        return self.dbconn.connect_to_db(host, user, pwd, dbname)

    def crawl_one_page(self, full_url: str):
        """
        爬取一个网页
        :param full_url: 网页url
        :return: None
        """
        try:
            content = HTTPtentacle.HTML_Downloader.HTMLDownloader.get_page_content(full_url)
        except UserWarning as e:
            print(e)
            self.connect_error_list.append(full_url)
            self.log_buffer += full_url + ": connect error\n"
            return False
        except UnicodeDecodeError as e:
            print(e)
            self.connect_error_list.append(full_url)
            self.log_buffer += full_url + ": decode error\n"
            return False

        self.partial_crawl_count += 1
        if self.__check_404_error(content["response_url"]):
            self.log_buffer += full_url + ": 404 page\n"
            self.partial_404_count += 1
            return False
        else:
            item = (full_url, content["response_url"], int(content["LemmaId"]), content["newLemmaIdEnc"],
                    content["html"])
            self.buffer_list.append(item)
            self.write_into_sql()
            return True

    def write_into_sql(self, force=False):
        """
        缓存达到设定值之后一次性写入数据库，或者强制写入
        :param force: 是否无视设定值强制写入
        :return: 是否写入了
        """
        if len(self.buffer_list) >= self.crawl_step_length or force:
            print("pid:{}------------- writing mysql and log".format(os.getpid()))
            columns = ['old_url', 'url', 'lemmaid', 'newlemmaidenc', 'html_data']
            self.dbconn.insert_unique('item_raw', columns, self.buffer_list)
            self.buffer_list.clear()
            self.write_log(True)
            return True
        else:
            return False

    def write_log(self, force=True):
        """
        写log
        :param force:
        :return:
        """
        if force:
            self.error_404_count += self.partial_404_count
            self.crawled_page_count += self.partial_crawl_count
            time_span = time.time() - self.timestamp
            log_content = ('\n',
                           'LOG---START---------------------------------------------------\n',
                           time.ctime(time.time()),
                           '\npid:{}\n'.format(os.getpid()),
                           self.log_buffer,
                           "\nprocess section:{}, 404 section:{},\n"
                           .format(self.partial_crawl_count, self.partial_404_count),
                           "\nprocess total:{}, 404 total:{}, time cost:{} secs\n"
                           .format(self.crawled_page_count, self.error_404_count, time_span),
                           'Error list:\n{}'.format('\n'.join(self.connect_error_list)),
                           '\nLOG----END----------------------------------------------------')
            self.connect_error_list.clear()

            self.partial_crawl_count = 0
            self.partial_404_count = 0
            with open(self.logfile_dir, 'a', encoding='utf-8') as logfile:
                logfile.writelines(log_content)
            self.log_buffer = ""
            self.timestamp = time.time()

    def log_append(self, string):
        self.log_buffer += string

    @staticmethod
    def __check_404_error(url):
        if re.match("https://baike.baidu.com/error", url) is None:
            return False
        else:
            return True


if __name__ == '__main__':
    pass
