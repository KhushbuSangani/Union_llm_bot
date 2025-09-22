from utils.db_connector import execute_query
from datetime import datetime, timedelta
import random


def fetch_chats():
    # my_collection = db_connection["conversations"]
    # chat_collection = db_connection['fallback_chats']
    # data = my_collection.find({})
    # query = []
    # response = []
    # intent = []
    # count = 0
    # for i in data:
    #     for j in i['events']:
    #         if 'text' in j:
    #             count = count + 1
    #             if count % 2 == 0:
    #                 response.append(j['text'])
    #             else:
    #                 query.append(j['text'])
    #         if 'name' in j and 'utter' in j['name']:
    #             intent.append(j['name'][6:])

    # chats = []
    # for queries, responses, intents in zip(query, response, intent):
    #     if len(queries) < 100:
    #         chats.append({'intent': intents, 'queries': queries, 'response': responses})
    # chat_collection.insert_many(chats)
    # cursor = chat_collection.find().sort([("_id", -1)]).skip(50)
    # for document in cursor:
    #     try:
    #         chat_collection.delete_one({"_id": document["_id"]})
    #     except Exception as e:
    #         print("Error deleting document:", str(e))
    # return chats

    sql_query = "SELECT * FROM conversation ORDER BY id desc"

    chat_data = execute_query(sql_query, "select")
    return chat_data
def fetch_cache_questions(limit, offset, collection_name=None, created_by=None, query_text=None, response_text=None):
    base_query = """
        SELECT * FROM (
            SELECT c.*, a.username, ROW_NUMBER() OVER (ORDER BY c.id DESC) AS rnum
            FROM conversation c
            LEFT JOIN admin_login a ON c.user_id = a.user_id
            WHERE c.ADMIN_ACTION = 'like'
    """

    # Params dict - start empty
    params = {}

    # Add conditions only if values are provided
    if collection_name:
        print(collection_name)
        base_query += " AND LOWER(JSON_VALUE(c.METADATA, '$.collection_name')) LIKE '%' || LOWER(:collection_name) || '%'"
        params['collection_name'] = collection_name

    if created_by:
        base_query += "AND LOWER(a.username) LIKE LOWER(:created_by)"
        params["created_by"] = f"%{created_by}%"

    if query_text:
        base_query += " AND LOWER(c.QUERY) LIKE LOWER(:query_text)"
        params['query_text'] = f"%{query_text}%"

    if response_text:
        base_query += " AND LOWER(c.RESPONSE_TEXT) LIKE LOWER(:response_text)"
        params['response_text'] = f"%{response_text}%"

    # Close the inner subquery
    base_query += """
        )
        WHERE rnum > :start_row AND rnum <= :end_row
    """

    # Add pagination params
    params['start_row'] = offset
    params['end_row'] = offset + limit

    print(base_query, 888888888888888888888888888888888888888888)
  

    try:
        results = execute_query(base_query, "select", params=params)
        print(results,9999999999993333333333333333333333)
        return results
    except Exception as e:
        print(e, 99999999999999999999999)
        return {'error': str(e)}
def fetch_user_feedback_and_tickets():
    sql_query="""
    SELECT DISTINCT
    c.ID as id,
    c.QUERY AS query,
    c.USER_ACTION AS user_action,
    c.RESPONSE_TEXT AS response_text,
    c.TIMESTAMP AS timestamp,
    c.USER_ID AS user_id,
    q.requestid as ticket_id,
    JSON_VALUE(c.METADATA, '$.ticket_id') AS ticket_id,
    CASE 
        WHEN c.USER_ACTION = 'dislike' THEN q.STATUS 
        ELSE NULL 
    END AS status,
    CASE 
        WHEN c.USER_ACTION = 'dislike' THEN q.DESCRIPTION 
        ELSE NULL 
    END AS description
    FROM CONVERSATION c
    LEFT JOIN GP_USER_QUERY q 
    ON JSON_VALUE(c.METADATA, '$.ticket_id') = q.REQUESTID where c.USER_ACTION is not null ORDER BY c.TIMESTAMP DESC"""
    chat_data = execute_query(sql_query, "select")
    return chat_data
    