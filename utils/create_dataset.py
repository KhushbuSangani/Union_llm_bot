"""
Converts training data into YAML format which is used to train rasa model
"""

from utils.db_connector import execute_query
import yaml
from typing import List
from utils.create_actions import CustomActionGeneratior


def str_presenter(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, str_presenter)
yaml.representer.SafeRepresenter.add_representer(str, str_presenter)


def fetch_intent():
    """Get intents from database and create list of intents

    Returns:
        list[str]: List of training intents fetched from database.
    """
    nlu_data = execute_query(
        """SELECT * FROM nlu_data WHERE status != '7'""", opration="select"
    )
    intents = [record["intent"] for record in nlu_data]
    return intents


def fetch_response():

    query = """SELECT * FROM nlu_data"""  # nlu_data
    nlu_data = execute_query(query, opration="select")
    responses = {}
    for records in nlu_data:

        if records["response_type"] == "buttons":
            for i in records["response_payload"]:
                a = "utter_" + records["intent"]
                if a not in responses:
                    responses[a] = [
                        {
                            "text": records["response_text"],
                            "buttons": [{"title": i[0], "payload": i[1]}],
                        }
                    ]
                else:
                    responses[a][0]["buttons"].append({"title": i[0], "payload": i[1]})

        if records["response_type"] == "text":
            if isinstance(records["response_text"], list):
                for i in records["response_text"]:
                    a = "utter_" + records["intent"]
                    if a not in responses:
                        responses[a] = [{"text": i, "intent": records["intent"]}]

            else:
                a = "utter_" + records["intent"]
                if a not in responses:
                    # responses[a] = [{"text": records['response_text'],'intent':records["intent"]}]

                    responses[a] = [{"text": records["response_text"]}]
    return responses


def fetch_nlu():
    """Get NLU data from database. intents and its examples
    eg: [{"intent": "greet","examples": "- hey\n- hello\n- hi\n- hello there\n- hey there\n"}]

    Returns:
        List[Dict[str]]: intent and expected input query
    """
    query = """SELECT * FROM nlu_data"""  # nlu_data
    nlu_data = execute_query(query, opration="select")
    responses = {}
    nlu = []
    query1 = []
    for records in nlu_data:
        query = ""
        responses["utter_" + records["intent"]] = [{"text": records["response_text"]}]
        query = ""

        queries = records["query"]
        for queri in queries:
            query1.append(queri)
            query = query + "- " + queri + "\n"
        nlu.append({"intent": records["intent"], "examples": str(query)})
        # print(nlu)
    return nlu


def construct_nlu_rules(input_intents: List[str]):
    """construct nlu rules
    eg:
    [{"rule": "description of rule/intent",
    "steps": [{"intent": "greet"}, {"action": "utter_greet"}]}

    Args:
        input_intents (List[str]): list of intents fetched from database

    Returns:
        List[Dict,Dict]: list of dictionaries containing intent and its response
    """
    constructed_rules = []
    for _intent in input_intents:
        single_rule = {}
        # static description for every intent
        single_rule["rule"] = "intent_desc"
        single_rule["steps"] = [{"intent": _intent}, {"action": f"utter_{_intent}"}]
        constructed_rules.append(single_rule)
    return constructed_rules


def fetch_temp_response():
    """Get intent responses from database and create list of dict containing responses
    eg: {'utter_intent': [{'text': 'sample_response'}]}

    Returns:
        Dict[List[Dict[str]]]: Dictionary containing list of intent response feteched from database
    """
    query = """SELECT * FROM nlu_data where status!= '7'"""
    nlu_data = execute_query(query, "select")
    responses = {}
    for records in nlu_data:
        if type(records["response"]) == str:
            responses["utter_" + records["intent"]] = [{"text": records["response"]}]
        else:
            responses["utter_" + records["intent"]] = []
            for i in records["response"]:
                responses["utter_" + records["intent"]].append({"text": i})
    return responses


def fetch_stories():
    query = """SELECT * FROM nlu_data"""  # nlu_data
    nlu_data = execute_query(query, opration="select")
    data_steps = {}
    steps = []
    stories = []
    data_steps["story"] = "happy"
    for records in nlu_data:
        intents = {}
        responses = {}
        intents["intent"] = records["intent"]
        responses["action"] = "utter_" + records["intent"]
        steps.append(intents)
        steps.append(responses)
    data_steps["steps"] = steps
    # custom_story = db_connection["custom_story"]
    stories.append(data_steps)
    return stories


def fetch_entities():
    """get entities from database

    Returns:
        List[str]: list of entities
    """
    query = """SELECT * FROM nlu_data"""  # nlu_data
    nlu_data = execute_query(query, opration="select")
    entities = []
    for records in nlu_data:
        if "entities" in records:
            for entity in records["entities"]:
                entities.append(entity)
    return entities


def fetch_slots():
    """_summary_

    Returns:
        _type_: _description_
    """
    query = """SELECT * FROM nlu_data"""  # nlu_data
    nlu_data = execute_query(query, opration="select")
    slots = {}

    for records in nlu_data:
        if "entities" in records:
            for i in records["entities"]:
                slots.update(
                    {
                        i: {
                            "type": "rasa.shared.core.slots.TextSlot",
                            "mappings": [{"type": "from_entity", "entity": i}],
                        }
                    }
                )
    return slots


def     get_training_set():
    pipeline = [
        {"name": "WhitespaceTokenizer"},
        {"name": "CountVectorsFeaturizer"},
        {"name": "DIETClassifier", "epochs": 200},
        {"name": "EntitySynonymMapper"},
        {"name": "ResponseSelector", "epochs": 200},
        {"name": "FallbackClassifier", "threshold": 0.8},
        {"name": "SpacyNLP", "model": "en_core_web_md"},
        {"name": "SpacyEntityExtractor"},
    ]
    policies = [
        {"name": "MemoizationPolicy", "max_history": 3},
        {"name": "TEDPolicy", "max_history": 5, "epochs": 200},
        {
            "name": "RulePolicy",
            "core_fallback_threshold": 0.4,
            "core_fallback_action_name": "action_default_fallback",
            "enable_fallback_prediction": True,
        },
    ]
    intents = fetch_intent()
    entities = fetch_entities()
    slots = fetch_slots()
    actions = []

    forms = {}
    e2e_actions = []
    responses = fetch_response()
    session_config = {
        "session_expiration_time": 60,
        "carry_over_slots_to_new_session": True,
    }

    rules = construct_nlu_rules(intents)

    nlu = fetch_nlu()

    stories = fetch_stories()

    data = {
        "version": "3.1",
        "recipe": "default.v1",
        "language": "en",
        "intents": intents,
        "entities": entities,
        "actions": actions,
        "slots": slots,
        "forms": forms,
        "e2e_actions": e2e_actions,
        "responses": responses,
        "session_config": session_config,
        "nlu": nlu,
        "rules": rules,
        "stories": stories,
        "pipeline": pipeline,
        "policies": policies,
    }

    training_data = yaml.safe_dump(
        data, indent=2, default_flow_style=False, sort_keys=False
    )
    print(training_data)
    return training_data
