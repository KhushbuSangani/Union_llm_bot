import oracledb as cx_Oracle
import json
from utils import config

def check_oracle_database():
    try:
        connection = cx_Oracle.connect(user=config.ORACLE_USER, password=config.ORACLE_PASSWORD, dsn=config.ORACLE_HOST)
        cursor = connection.cursor()
        cursor.execute('SELECT 1 FROM dual')
        cursor.close()
        connection.close()
        return True
    except cx_Oracle.DatabaseError:
        return False

def create_connection():
    return cx_Oracle.connect(
        user=config.ORACLE_USER, password=config.ORACLE_PASSWORD, dsn=config.ORACLE_HOST
    )


def close_connection(connection, cursor):
    cursor.close()
    connection.close()


def handle_lob_fields(row_dict):
    for key, value in row_dict.items():
        if isinstance(value, cx_Oracle.LOB):
            try:
                decoded_value = json.loads(value.read())
                row_dict[key] = decoded_value
            except json.JSONDecodeError as e:
                row_dict[key] = value.read()
                pass
        elif not isinstance(value, (int, float, bool, str, type(None))):
            # If it's neither a LOB nor a known simple type, handle it based on your requirements
            # For example, you can convert it to a string or handle it in a specific way
            row_dict[key] = value
    return row_dict


def execute_query(query, opration, params=None, fetch_one=False):
    connection = create_connection()
    cursor = connection.cursor()
    try:
        if opration == "select":
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            if fetch_one:
                result = cursor.fetchone()
            else:
                result = cursor.fetchall()
            if result:
                headers = [header[0].lower() for header in cursor.description]
                if fetch_one:
                    result = dict(zip(headers, result))

                    handle_lob_fields(result)
                    result = [result]
                else:
                    result = [dict(zip(headers, row)) for row in result]
                    for row_dict in result:
                        handle_lob_fields(row_dict)
            return result
        elif opration == "insert":
            if isinstance(params, list):
                cursor.executemany(query, params)
            else:
                cursor.execute(query, params)
            connection.commit()
            return {"message": "Insertion successful"}
        elif opration == "delete":
            if isinstance(params, list):
                cursor.executemany(query, params)
            else:
                cursor.execute(query, params)
            connection.commit()
            return {"message": "Deleted successful"}
        elif opration == "update":
            if isinstance(params, list):
                cursor.executemany(query, params)
            else:
                cursor.execute(query, params)
            connection.commit()
            return {"message": "updated successful"}

    except Exception as e:
        return {"error": f"Error executing query: {e}"}
    finally:
        close_connection(connection, cursor)


db_connection = execute_query
