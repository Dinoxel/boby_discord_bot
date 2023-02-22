import pymysql
import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_PORT = os.getenv('MYSQL_PORT')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')


class MysqlConnection:
    def __init__(self,
                 table: str | None = None,
                 is_committing: bool = True,
                 execute_many: bool = True,
                 delete_before: bool = False):
        self.is_committing = is_committing
        self._execute_many = execute_many
        self._delete_before = delete_before
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

    def commit(self):
        if self.is_committing:
            self.connection.commit()
            print(f"Committing changes to `{self._table}` database.")

    def _execute(self, sql_query, params=None):
        try:
            with self.connection:
                with self.connection.cursor() as cursor:
                    if self._delete_before:
                        cursor.execute(f"TRUNCATE `{self._table}`")

                    if self._execute_many:
                        cursor.executemany(sql_query, params)
                    else:
                        cursor.execute(sql_query, params)

                self.commit()

        except (MySQLdb.Error, MySQLdb.Warning) as mysql_error:
            print(mysql_error)
            return None

    def fetch_all(self, sql_query, params=None, output_type="dict"):
        with self.connection:
            with self.connection.cursor() as cursor:
                cursor.execute(sql_query, params)
                result_data = cursor.fetchall()
                column_names = [col[0] for col in cursor.description]

                if output_type in {"dict", "dictionary"}:
                    return [dict(zip(column_names, row)) for row in result_data]
                else:
                    return result_data, column_names
