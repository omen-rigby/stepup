import os
import psycopg2
import urllib.parse as up


DB_PATH = os.environ["DB_URL"]


def connect(db_path=DB_PATH):
    """Currently postgres is used yet mysql still has a chance"""
    url = up.urlparse(db_path)
    return psycopg2.connect(database=url.path[1:],
                            user=url.username,
                            password=url.password,
                            host=url.hostname,
                            port=url.port
                            )
    # db_url, db_name = db_path.rsplit('/', 1)
    # return connector.connect(
    #     host=db_url,
    #     user=user,
    #     password=pwd,
    #     database=db_name)


