from app import app
from utils import super_admin_model
from utils import model_data
from utils import create_dataset
from utils import fallback_handler


def test_dashboard():
    with app.test_client() as test_client:
        response = test_client.get("/")
        # happy flow
        assert response.status_code == 200


def test_admin_role_access():
    expected = super_admin_model.admin_role_access("4")
    assert expected == "Pending List"
    unexpected = super_admin_model.admin_role_access("4")
    assert unexpected == "Pending List"


def test_update_fetch_intent():
    nlu_list = ["166728835731", "166728835732"]
    expected = model_data.update_fetch_intent(nlu_list)
    assert type(expected) == list


def test_update_fetch_response():
    nlu_list = ["166728835731", "166728835732"]
    expected = model_data.update_fetch_response(nlu_list)
    assert type(expected) == dict


def test_update_fetch_nlu():
    nlu_list = ["166728835731", "166728835732"]
    expected = model_data.update_fetch_nlu(nlu_list)
    assert type(expected) == list


def test_construct_nlu_rules():
    nlu_list = ["166728835731", "166728835732"]
    expected = model_data.construct_nlu_rules(nlu_list)
    assert type(expected) == list


def test_update_fetch_stories():
    nlu_list = ["166728835731", "166728835732"]
    expected = model_data.update_fetch_stories(nlu_list)
    assert type(expected) == list


def test_update_fetch_entities():
    nlu_list = ["166728835731", "166728835732"]
    expected = model_data.update_fetch_entities(nlu_list)
    assert type(expected) == list


def test_update_fetch_slots():
    nlu_list = ["166728835731", "166728835732"]
    expected = model_data.update_fetch_slots(nlu_list)
    assert type(expected) == dict


def test_update_fetch_custom_story():
    nlu_list = ["166728835731", "166728835732"]
    expected = model_data.update_fetch_custom_story(nlu_list)
    assert type(expected) == list


def test_get_training_set_update():
    nlu_list = ["166728835731", "166728835732"]
    expected = model_data.get_training_set_update(nlu_list)
    assert type(expected) == str


def test_fetch_intent():
    expected = create_dataset.fetch_intent()
    assert type(expected) == list


def test_fetch_response():
    expected = create_dataset.fetch_response()
    assert type(expected) == dict


def test_fetch_nlu():
    expected = create_dataset.fetch_nlu()
    assert type(expected) == list


def test_construct_nlu_rules_data():
    nlu_list = ["166728835731", "166728835732"]
    expected = create_dataset.construct_nlu_rules(nlu_list)
    assert type(expected) == list


def test_fetch_stories():
    expected = create_dataset.fetch_stories()
    assert type(expected) == list


def test_fetch_entities():
    expected = create_dataset.fetch_entities()
    assert type(expected) == list


def test_fetch_slots():
    expected = create_dataset.fetch_slots()
    assert type(expected) == dict


def test_fetch_custom_story():
    expected = create_dataset.fetch_custom_story()
    assert type(expected) == list


def test_get_training_set():
    expected = create_dataset.get_training_set()
    assert type(expected) == str


def test_fetch_chats():
    expected = fallback_handler.fetch_chats()
    assert type(expected) == list


def test_fetch_mismatch_chats():
    expected = fallback_handler.fetch_mismatch_chats()
    assert type(expected) == list
