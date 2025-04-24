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
    ON JSON_VALUE(c.METADATA, '$.ticket_id') = q.REQUESTID where c.USER_ACTION is not null ORDER BY C.TIMESTAMP DESC"""
    chat_data = execute_query(sql_query, "select")
    return chat_data
    