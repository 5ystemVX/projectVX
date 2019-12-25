from HTTPtentacle.Mysql_connector import MysqlConnector
import pprint
import time
import unittest


class MyTestCase(unittest.TestCase):
    @staticmethod
    def test_insert_query():
        conn = MysqlConnector()
        # 连接
        conn.connect_to_db(url="localhost", username="root", passwd="password", dbname="unit_test")

        # 表结构参数
        table_create_args = ["id int PRIMARY KEY AUTO_INCREMENT",
                             "name varchar(255)",
                             "address varchar(40)",
                             "age int"]
        # 建表
        conn.create_table("testtable", table_create_args)

        # 指定插入列
        columns = ["name", "address", "age"]

        # 数据数组
        values = []

        # 批量插入2000条，100一组
        start_time = time.time()
        for i in range(0, 2000):
            values.append(("aaaa", "aaa", i))
            if len(values) > 100:
                conn.insert_many("testtable", columns, values)
                values = []
        duration = time.time() - start_time
        print("批量操作------" + str(duration) + " secs")

        pprint.pprint(conn.query(["testtable"], limit=20))

        # 数据表重置
        conn.execute_raw_sql("DROP TABLE testtable")
        conn.create_table("testtable", table_create_args)

        # 单条插入2000条
        start_time = time.time()
        for i in range(0, 2000):
            conn.insert_one("testtable", {"name": "bbbb", "address": "bbb", "age": i})
        duration = time.time() - start_time
        print("单条操作------" + str(duration) + " secs")

        pprint.pprint(conn.query(["testtable"], limit=20))
        conn.execute_raw_sql("DROP TABLE testtable")
