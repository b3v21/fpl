import pandas as pd
import numpy as np
from player import Player

SEASON = "2025-26"
CURRENT_GW = 6
TOTAL_GWS = 38
GWS = range(CURRENT_GW, TOTAL_GWS + 1)

"""
Singleton class for storing and accessing data to be used in the engine
"""


class Dataloader:
    _instance = None
    _players: dict[int, Player] = None

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
            print(str(len(self._player_ids)) + " players found\n")
            self.make_players()

    # Build Player objects
    def make_players(self):
        self._players = {}
        for player_id in self._player_ids:
            self._players[player_id] = Player(
                id=player_id,
                price=self._player_price[player_id],
                name=self._player_name[player_id],
                team_name=self._player_team_name[player_id],
                team_code=self._player_team_code[player_id],
                team_id=self._team_code_team_id[self._player_team_code[player_id]],
                position=self._player_position[player_id],
                chance_of_playing=self._player_chance_of_playing[player_id],
                vs_team_id={t: self._team_vs_team[self._team_code_team_id[self._player_team[player_id]]] for t in GWS},
                vs_team_diff={t: self._player_fixture_difficulty[(player_id, t)] for t in GWS},
                xp={t: self._player_expected_points[(player_id, t)] for t in GWS},
            )

    @property
    def players(self):
        return self._players

    @property
    def team_id_team_code(self):
        return self._team_id_team_code
    
    @property
    def team_code_name(self):
        return self._team_code_name

    def build_lookups(self):
        player_data = pd.read_csv(f"data/{SEASON}/players_raw.csv")
        team_data = pd.read_csv(f"data/{SEASON}/teams.csv")
        fixtures = pd.read_csv(f"data/{SEASON}/fixtures.csv")

        #########################################################
        #                   Team Related Data
        #########################################################

        # Team code -> Team name (1)
        self._team_code_name = dict(zip(team_data["code"], team_data["short_name"]))

        # Player ID -> Team code (2)
        self._player_team_code = dict(zip(player_data["id"], player_data["team_code"]))

        # Player ID -> Team name (uses 1 & 2)
        self._player_team_name = {
            player_id: self._team_code_name[team] for player_id, team in zip(player_data["id"], player_data["team_code"])
        }

        # Team code -> Team ID
        self._team_code_team_id = dict(zip(team_data["code"], team_data["id"]))

        # Team ID -> Team code
        self._team_id_team_code = dict(zip(team_data["id"], team_data["code"]))

        #########################################################
        #                  Fixture Related Data
        #########################################################

        self._fixtures_gw = fixtures[fixtures["event"] == CURRENT_GW]

        # Team -> Team being played this GW
        self._team_vs_team = {}
        for row in self._fixtures_gw.itertuples():
            self._team_vs_team[row.team_h] = row.team_a
            self._team_vs_team[row.team_a] = row.team_h

        # Team -> Opposition team difficultly this GW
        self._team_diff = {}
        for row in self._fixtures_gw.itertuples():
            self._team_diff[row.team_h] = row.team_a_difficulty
            self._team_diff[row.team_a] = row.team_h_difficulty

        #########################################################
        #                  Player Related Data
        #########################################################

        # Player ID List
        self._player_ids = list(player_data["id"])

        # Player ID -> Name
        self._player_name = dict(
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
        self._player_price = dict(zip(player_data["id"], player_data["now_cost"]))

        # Player ID -> Expected Points this week
        self._player_expected_points = {(player_id, t): xp for player_id, xp in zip(player_data["id"], player_data["ep_this"]) for t in GWS}

        # Player ID -> Position
        self._player_position = {player_id: pos for player_id, pos in zip(player_data["id"], player_data["element_type"])}

        # Player ID -> Team Code
        self._player_team = {player_id: team_code for player_id, team_code in zip(player_data["id"], player_data["team_code"])}

        # Fixture Difficulty next week
        self._player_fixture_difficulty = {
            (player_id, t): self._team_diff[self._team_vs_team[self._team_code_team_id[team_code]]]
            for player_id, team_code in zip(player_data["id"], player_data["team_code"])
            for t in GWS
        }

        # Chance of playing this week
        self._player_chance_of_playing = dict(zip(player_data["id"], player_data["chance_of_playing_this_round"]))
