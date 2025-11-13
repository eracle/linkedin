# tests/test_actions.py
from linkedin.actions import connect, send_message

def test_connect_action(capfd):
    """
    Tests that the 'connect' action function prints the correct message.
    """
    linkedin_url = "https://www.linkedin.com/in/test-profile"
    params = {"message": "Hello, I'd like to connect!"}
    
    connect(linkedin_url, params)
    
    out, err = capfd.readouterr()
    assert out.strip() == f"ACTION: connect for {linkedin_url} with params: {params}"

def test_send_message_action(capfd):
    """
    Tests that the 'send_message' action function prints the correct message.
    """
    linkedin_url = "https://www.linkedin.com/in/test-profile"
    params = {"message": "Hello, this is a follow-up message."}
    
    send_message(linkedin_url, params)
    
    out, err = capfd.readouterr()
    assert out.strip() == f"ACTION: send_message to {linkedin_url} with params: {params}"
