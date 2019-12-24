import HTTPtentacle.Mysql_connector as conn

if __name__ == '__main__':
    dbconn = conn.MysqlConnector()
    dbconn.connect_to_db(url="localhost", username="root", passwd="password", dbname="baidu_test")
    dbconn.toggle_debug(True)
    table_args = ["old_url VARCHAR(255)",
                  "url VARCHAR(512) PRIMARY KEY",
                  "lemmaid INT",
                  "newlemmaidenc VARCHAR(30)",
                  "html_data LONGTEXT"]

    col = ['old_url', 'url', 'lemmaid', 'newlemmaidenc', 'html_data']
    for i in range(1, 20):
        item = ["old", "url-{}".format(i), "LemmaId", "newLemmaIdEnc", "html"]
    dbconn.create_table('item_raw', table_args, overwrite=False)
