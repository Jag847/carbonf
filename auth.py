# auth.py
import streamlit as st
import streamlit_authenticator as stauth
import yaml

# In requirements.txt: streamlit-authenticator,PyYAML

def load_auth():
    # This could be dynamically loaded from your DB instead of YAML.
    config = {
      'credentials': {
        'usernames': {
          'alice': {'email':'alice@example.com','name':'Alice','password':'hashed_pw'},
          # ...
        }
      },
      'cookie': {'expiry_days': 30, 'key': 'some_signature_key'},
      'preauthorized': {'emails': []}
    }
    return stauth.Authenticate(
      credentials=config['credentials'],
      cookie_name=config['cookie']['key'],
      key='some_signature_key',
      cookie_expiry_days=config['cookie']['expiry_days']
    )
