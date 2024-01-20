import mysql.connector as connector
DB_PATH = "omenrigby.mysql.pythonanywhere-services.com/omenrigby$default"
USER = "USER"
PWD = "PASS"


def connect(db_path=DB_PATH, user=USER, pwd=PWD):
    db_url, db_name = db_path.rsplit('/', 1)
    return connector.connect(
        host=db_url,
        user=user,
        password=pwd,
        database=db_name)


