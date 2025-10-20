import pandas as pd
from .player import Player
from constants import SEASON, PAST_GWS, FUTURE_GWS
from .team import Team
from .fixture import Fixture
from .predict_xp import train_model, predict
import heapq
import numpy as np

"""
Singleton class for storing and accessing data to be used in the engine
"""


class Dataloader:
    _instance = None
    _players: dict[int, Player] = {}
    _teams: dict[int, Team] = {}
    _fixtures: dict[int, Fixture] = {}

    def __new__(cls):
        if cls._instance is None:
            print("\nCreating a new instance of the DataLoader.")
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.initialized = True
            self.build_objects()

    @property
    def players(self):
        return self._players

    @property
    def teams(self):
        return self._teams

    @property
    def fixtures(self):
        return self._fixtures

    def build_objects(self):
        print("Building data objects...\n")

        player_data = pd.read_csv(f"data/{SEASON}/players_raw.csv")
        team_data = pd.read_csv(f"data/{SEASON}/teams.csv")
        fixtures = pd.read_csv(f"data/{SEASON}/fixtures.csv")
        merged_gw = pd.read_csv(f"data/{SEASON}/gws/merged_gw.csv")

        xp_data_dict = {}
        for gw in PAST_GWS:
            xp_data_dict[gw] = pd.read_csv(f"data/{SEASON}/gws/xP{gw}.csv")

        # Player ID List
        self._player_ids = list(player_data["id"])

        for _, row in team_data.iterrows():
            self._teams[row["id"]] = Team(row["id"], row["code"], row["short_name"], row["name"], row["strength"])

        # Player id -> Team ID
        self._player_team_id = dict(zip(player_data["id"], player_data["team"]))

        # Player id -> Team Obj
        self._player_team = {}
        for pid in self._player_ids:
            self._player_team[pid] = self._teams[self._player_team_id[pid]]

        print(str(len(self._teams)) + " teams loaded.")

        self._fixtures: dict[int, Fixture] = {}
        self._player_fixtures: dict[int, dict:[int, Fixture]] = {}

        for _, row in fixtures.iterrows():
            code = row["code"]
            gw = row["event"]
            team_h = self._teams[row["team_h"]]
            team_a = self._teams[row["team_a"]]

            new_fixture = Fixture(code, team_h, team_a, gw)
            self._fixtures[code] = new_fixture

        for pid in self._player_ids:
            self._player_fixtures[pid] = {
                fix.gw: fix
                for fix in self._fixtures.values()
                if self._player_team[pid].id == fix.team_a.id or self._player_team[pid].id == fix.team_h.id
            }

        print(str(len(self._fixtures)) + " fixtures loaded.")

        for pid in self._player_ids:
            player = Player(pid, player_data[player_data.id == pid], self._player_team[pid], self._player_fixtures[pid])
            self._players[pid] = player

        print(str(len(self._players)) + " players loaded.\n")

        print("Loading XP Data...")
        players = list(self._players.values())
        model, training_data_count = train_model(merged_gw, players)
        predict(model, players, merged_gw)
        print(f"XP model trained with {training_data_count} data points.\n")

        print("Removing players with < 2 avg XP...\n")
        self._players = {id: player for (id, player) in self._players.items() if np.mean([player.future_xp[gw] for gw in FUTURE_GWS]) >= 2}

        # haaland = self._players[430].future_xp
        
        # for gw, xp in haaland.items():
        #     print(f"GW {gw}: {xp * DECAY ** (gw + 1 - CURRENT_GW)} xp")
        # print(heapq.nlargest(5, [(player.name, player.future_xp[CURRENT_GW]) for player in self._players.values()], key=lambda x: x[1]))
