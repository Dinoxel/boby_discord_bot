import pymysql
import os
import numpy as np
import pandas as pd

from datetime import datetime, timezone

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_PORT = os.getenv('MYSQL_PORT')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')


class MysqlConnection:
    def __init__(self,
                 table: str | None = None):
        self.connection = pymysql.connect(host=MYSQL_HOST,
                                          port=int(MYSQL_PORT),
                                          user=MYSQL_USER,
                                          password=MYSQL_PASSWORD,
                                          database=MYSQL_DATABASE)
        self._table = table

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()

    def fetch_all(self, sql_query: str | None = None, params=None, output_type="dict"):
        if sql_query is None:
            sql_query = f"SELECT * FROM `{self._table}`"
        with self.connection:
            with self.connection.cursor() as cursor:
                cursor.execute(sql_query, params)
                result_data = cursor.fetchall()
                column_names = [col[0] for col in cursor.description]

                if output_type in {"dict", "dictionary"}:
                    return [dict(zip(column_names, row)) for row in result_data]
                elif output_type in {"df", "dataframe"}:
                    return pd.DataFrame(result_data, columns=column_names)
                elif output_type in {"cols", "columns"}:
                    return column_names
                elif output_type == "rows":
                    return result_data
                else:
                    return result_data, column_names
