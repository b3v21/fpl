API_URL = "https://fantasy.premierleague.com/api"
ELEMENT_SUMMARY = "/element-summary/1"

import requests
import json


def fetch_data():
    """
    fetches data from the fpl api (https://fantasy.premierleague.com/api) and builds objects
    for use in the engine
    """
    req = requests.get(API_URL + ELEMENT_SUMMARY)

    if req.status_code == 200:
        json_res = req.json()

    print(json.dumps(json_res, indent=4))
    return


if __name__ == "__main__":
    fetch_data()
