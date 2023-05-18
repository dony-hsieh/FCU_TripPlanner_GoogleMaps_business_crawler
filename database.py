import MySQLdb
import pathlib
import os
from dotenv import load_dotenv

from definitions import DOTENV, ENVVAR_KEY


class Database:
    def __init__(self):
        self.conn = None
        try:
            if not load_dotenv(pathlib.Path(DOTENV).absolute()):
                print("[*] Found no .env file or set environment failed")
                return
            self.conn = MySQLdb.connect(
                host=os.getenv(ENVVAR_KEY[0], ""),
                port=int(os.getenv(ENVVAR_KEY[1], 0)),
                user=os.getenv(ENVVAR_KEY[2], ""),
                password=os.getenv(ENVVAR_KEY[3], ""),
                db=os.getenv(ENVVAR_KEY[4], "")
            )
            print("[*] Database connected successfully")
        except MySQLdb.Error as error:
            print(error.args)

    def __del__(self):
        if self.conn is not None:
            self.conn.close()

    def execute_R(self, statement: str, args: tuple = (), fetch_counts: int = 0) -> tuple:
        """
        :param statement: SQL statement.
        :param args: Arguments to inject into SQL statement.
        :param fetch_counts: 0 is fetchall(), others are fetchmany().
        :return: A tuple contains some row data.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(statement, args)
            if fetch_counts == 0:
                return cursor.fetchall()
            if fetch_counts > 0:
                return cursor.fetchmany(fetch_counts)
        except MySQLdb.Error as error:
            print(error.args)
        return tuple()

    def execute_CUD(self, statement: str, args: tuple = ()):
        """
        :param statement: SQL statement.
        :param args: Arguments to inject into SQL statement.
        :return: None.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(statement, args)
            self.conn.commit()
        except MySQLdb.Error as error:
            print(error.args)


if __name__ == "__main__":
    db = Database()
