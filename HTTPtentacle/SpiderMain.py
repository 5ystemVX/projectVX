import os
import queue
import time
import warnings
import HTTPtentacle.Spider
import multiprocessing


def spider_run(mp_queue: multiprocessing.Queue, stop_sign: multiprocessing.Value):
    """
    爬虫子线程的执行方法
    :param mp_queue: url池队列，爬虫消耗其中的url
    :param stop_sign: 停止记号，由主函数控制。置为True的时候爬虫准备收尾停止运行。
    :return None: 无返回值，直接与数据库交互。
    """
    SLEEP_TIME = 0.7
    print('pid: {}---starting'.format(os.getpid()))
    spider = HTTPtentacle.Spider.SpiderSlave(step_length=10, log_dir="../debug_scripts/debug_html/spiders_log.log")
    try:
        spider.connect_sql("localhost", "root", "password", 'baidu_test')
    except:
        ('pid: {}---mysql connect error'.format(os.getpid()))
        exit(0)
    while True:  # 线程主循环
        if stop_sign.value == 1:
            print('pid: {}---terminate sign received'.format(os.getpid()))
            break
        else:
            try:
                http_url = mp_queue.get(timeout=10)
            except queue.Empty:
                # 获取url超时
                continue
            print('pid:{}-----processing:{} ------wait {} sec'.format(os.getpid(), http_url, SLEEP_TIME))
            spider.crawl_one_page(http_url)
            time.sleep(SLEEP_TIME)  # 添加延迟，防反爬

    # 通知结束，spider收尾
    spider.write_log(True)
    spider.write_log(force=True)
    exit(0)


def dummy_run(mp_queue: multiprocessing.Queue, stop_sign: multiprocessing.Value):
    print('pid: {}---starting'.format(os.getpid()))
    while True:  # 线程主循环
        if stop_sign.value == 1:
            print('pid: {}---terminate sign received'.format(os.getpid()))
            break
        else:
            try:
                var = mp_queue.get(timeout=5)
            except queue.Empty:
                print('pid: {}---empty queue'.format(os.getpid()))
                # 获取url超时
                continue
            print('pid:{}-----processing{} ------wait 1 sec'.format(os.getpid(), var))
            time.sleep(1.5)
    # 通知结束，spider收尾
    print('pid: {}---exiting'.format(os.getpid()))
    exit(0)


if __name__ == '__main__':

    warnings.filterwarnings("ignore")
    url_queue = multiprocessing.Queue()
    end_signal = multiprocessing.Value('i', 0)
    for i in range(1, 500):
        url_queue.put("https://baike.baidu.com/view/{}".format(i))
    CRAWLER_NUM = 4
    crawler_reg_list = []
    while len(crawler_reg_list) < CRAWLER_NUM:
        process = multiprocessing.Process(target=spider_run, args=(url_queue, end_signal))
        crawler_reg_list.append(process)
        process.daemon = True
        process.start()
    while not url_queue.empty():
        time.sleep(45)
        for crawler in crawler_reg_list:  # 检查全部线程是否存活
            if not crawler.is_alive():  # 替换死进程
                crawler_reg_list.remove(crawler)
                process = multiprocessing.Process(target=spider_run, args=(url_queue, end_signal))
                process.daemon = True
                process.start()
                crawler_reg_list.append(process)

        # 管理进程生命周期
        print('----------------main-checking----------------------------------------')
    end_signal.value = 1
    # 等待所有进程自行结束
    for crawler in crawler_reg_list:
        crawler.join()
    print('main-exit')
