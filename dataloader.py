import pandas as pd
import numpy as np

SEASON = "2025-26"
CURRENT_GW = 6

"""
Singleton class for storing and accessing data to be used in the engine
"""


class Dataloader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            print("\nCreating a new instance of the DataLoader.")
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.initialized = True
            print("Building lookups")
            self.build_lookups()
            print(str(len(self.player_ids)) + " players found\n")

    def build_lookups(self):
        player_data = pd.read_csv(f"data/{SEASON}/players_raw.csv")
        team_data = pd.read_csv(f"data/{SEASON}/teams.csv")
        fixtures = pd.read_csv(f"data/{SEASON}/fixtures.csv")

        #########################################################
        #                   Team Related Data
        #########################################################

        # Team code -> Team name (1)
        self.team_code_name = dict(zip(team_data["code"], team_data["short_name"]))

        # Player ID -> Team code (2)
        self.player_team_code = zip(player_data["id"], player_data["team_code"])

        # Player ID -> Team name (uses 1 & 2)
        self.player_team_name = {player_id: self.team_code_name[team] for player_id, team in self.player_team_code}

        # Team code -> Team ID
        self.team_code_team_id = dict(zip(team_data["code"], team_data["id"]))

        #########################################################
        #                  Fixture Related Data
        #########################################################

        self.fixtures_gw = fixtures[fixtures["event"] == CURRENT_GW]

        # Team -> Team being played this GW
        self.team_vs_team = {}
        for row in self.fixtures_gw.itertuples():
            self.team_vs_team[row.team_h] = row.team_a
            self.team_vs_team[row.team_a] = row.team_h

        # Team -> Opposition team difficultly this GW
        self.team_diff = {}
        for row in self.fixtures_gw.itertuples():
            self.team_diff[row.team_h] = row.team_a_difficulty
            self.team_diff[row.team_a] = row.team_h_difficulty

        #########################################################
        #                  Player Related Data
        #########################################################

        # Player ID List
        self.player_ids = list(player_data["id"])

        # Player ID -> Name
        self.player_name = dict(
            zip(
                player_data["id"],
                map(
                    lambda n1, n2: n1 + " " + n2,
                    player_data["first_name"],
                    player_data["second_name"],
                ),
            )
        )

        # Player ID -> Price (as of now)
        self.player_price = dict(zip(player_data["id"], player_data["now_cost"]))

        # Player ID -> Expected Points this week
        self.player_expected_points = dict(zip(player_data["id"], player_data["ep_this"]))

        # Player ID -> Position Mask (o.t.f [1,0,0,0])
        self.player_position_mask = {
            player_id: [int(x == element_type) for x in range(1, 5)]  # place a '1' in the index which corresponds to the players position
            for player_id, element_type in zip(player_data["id"], player_data["element_type"])
        }

        # Player ID -> Team Mask (o.t.f [1,0,0,0,...,0] (length of 20))
        self.player_team_mask = {
            player_id: {
                tc: int(tc == team_code) for tc in self.team_code_name.keys()
            }  # place a '1' in the index which corresponds to the players position
            for player_id, team_code in zip(player_data["id"], player_data["team_code"])
        }

        # Fixture Difficulty next week
        self.player_fixture_difficulty = {
            player_id: self.team_diff[self.team_vs_team[self.team_code_team_id[team_code]]]
            for player_id, team_code in zip(player_data["id"], player_data["team_code"])
        }

        # Chance of playing this week
        self.player_chance_of_playing = dict(zip(player_data["id"], player_data["chance_of_playing_this_round"]))
