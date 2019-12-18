import requests
import re


class HTMLDownloader(object):
    @staticmethod
    def get_page_content(url: str, header: dict = None, retry_time: int = 3) -> tuple:
        """
        获取HTML页面全部文字内容，去除js和css等装饰信息。
            :param url:网页URL，包括http协议头
            :param header:html请求头
            :param retry_time 尝试重连次数
            :return  网页所有信息,响应的url
            :except  UserWarning 连接失败抛出异常
        """

        (html, response_url) = HTMLDownloader.get_raw_page(url, header, retry_time)
        # 削去多余的空白符号，保留单个桩
        html = re.sub(r'[\n\r\t]', '\n', html)
        html = re.sub(r'\n+', '\n', html)
        html = re.sub(r' +', " ", html)
        # 削去 所有的 style 区域，精简结果
        html = re.sub(r'<style.*?>.*?/style>', "###style texts###", html, flags=re.S)
        # 削去所有 js 内容（可能有问题）
        html = re.sub(r'<script.*?>.*?/script>', "###java script###", html, flags=re.S)
        # 返回页面内容和真实响应url
        return html, re.sub(r'\?.*', '', response_url)  # 去除get参数部分

    @staticmethod
    def get_raw_page(url: str, header: dict = None, retry_time: int = 3) -> tuple:
        """
        获取HTML页面全部原生内容。
            :param url:网页URL，包括http协议头
            :param header:html请求头
            :param retry_time 尝试重连次数
            :return  网页所有信息,响应的url
            :except  UserWarning 连接失败抛出异常
        """

        # 处理/生成请求头
        if header is None:
            # 生成默认请求头
            internal_header = {"Accept": "*/*",
                               "Accept-Language": "en-US,en;q=0.8",
                               "Cache-Control": "max-age=0",
                               "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) \
                                                AppleWebKit/537.36 (KHTML, like Gecko) \
                                                Chrome/48.0.2564.116 Safari/537.36",
                               "Connection": "keep-alive"
                               }
        else:
            internal_header = header

        # 尝试 @retry_time 次连接
        fail_count = 0
        if retry_time < 1:
            retry_time = 1
        while fail_count < retry_time:
            try:
                # 获取内容
                response = requests.get(url, headers=internal_header, timeout=5)
                response.raise_for_status()
            except:
                # 记录失败，重试连接
                fail_count += 1
                # debug output
                print("connection fail %s" % fail_count)
                continue
            else:
                # 获取成功操作
                # 组织页面的全部信息
                result = response.content.decode("utf-8")
                return result, response.url
                # 连接失败，抛异常
        raise UserWarning("connection failed {} times.".format(retry_time))


# 测试代码
if __name__ == "__main__":
    a = HTMLDownloader.get_page_content("https://baike.baidu.com/view/111")
    print(a)
