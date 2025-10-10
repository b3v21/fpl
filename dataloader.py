import pandas as pd
from player import Player
from constants import SEASON, CURRENT_GW, FUTURE_GWS, PAST_GWS
from regression import regression
from team import Team

"""
Singleton class for storing and accessing data to be used in the engine
"""


class Dataloader:
    _instance = None
    _players: dict[int, Player] = {}
    _teams: dict[int, Team] = {}

    def __new__(cls):
        if cls._instance is None:
            print("\nCreating a new instance of the DataLoader.")
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.initialized = True
            self.build_lookups()
            self.make_players()

    # Build Player objects
    def make_players(self):

        for player_id in self._player_ids:
            if self._player_future_xp[(player_id, CURRENT_GW)] >= 2:  # as a heuristic, only include players with xp >= 2 for next week
                self._players[player_id] = Player(
                    id=player_id,
                    price=self._player_price[player_id],
                    name=self._player_name[player_id],
                    team=self._player_team[player_id],
                    position=self._player_position[player_id],
                    chance_of_playing=self._player_chance_of_playing[player_id],
                    vs_team_id={t: self._team_vs_team[(self._player_team_id[player_id], t)] for t in FUTURE_GWS},
                    vs_team_diff={t: self._player_fixture_difficulty[(player_id, t)] for t in FUTURE_GWS},
                    prev_xp={t: self._player_previous_xp[(player_id, t)] for t in PAST_GWS},
                    future_xp={t: self._player_future_xp[(player_id, t)] for t in FUTURE_GWS},
                )

        print(str(len(self._players)) + " players generated\n")

    @property
    def players(self):
        return self._players

    @property
    def teams(self):
        return self._teams

    @property
    def team_vs_team(self):
        return self._team_vs_team
    
    @property
    def player_future_xp(self):
        return self._player_future_xp
    

    def build_lookups(self):
        print("Building lookups")

        player_data = pd.read_csv(f"data/{SEASON}/players_raw.csv")
        team_data = pd.read_csv(f"data/{SEASON}/teams.csv")
        fixtures = pd.read_csv(f"data/{SEASON}/fixtures.csv")
        xp_data_dict = {}

        for gw in PAST_GWS:
            xp_data_dict[gw] = pd.read_csv(f"data/{SEASON}/gws/xP{gw}.csv")

            # Player ID List
            self._player_ids = list(player_data["id"])

        #########################################################
        #                   Team Related Data
        #########################################################

        for _, row in team_data.iterrows():
            self._teams[row["id"]] = Team(row["id"], row["code"], row["short_name"], row["name"], row["strength"])

        # Player id -> Team ID
        self._player_team_id = dict(zip(player_data["id"], player_data["team"]))

        # Player id -> Team Obj
        self._player_team = {}
        for pid in self._player_ids:
            self._player_team[pid] = self._teams[self._player_team_id[pid]]

        #########################################################
        #                  Fixture Related Data
        #########################################################
        self._team_vs_team = {}
        self._team_diff = {}

        for fixture in FUTURE_GWS:
            self._fixtures_gw = fixtures[fixtures["event"] == fixture]

            # Team -> Team being played this GW
            for row in self._fixtures_gw.itertuples():
                self._team_vs_team[(row.team_h, fixture)] = row.team_a
                self._team_vs_team[(row.team_a, fixture)] = row.team_h

            # Team -> Opposition team difficultly this GW
            for row in self._fixtures_gw.itertuples():
                self._team_diff[(row.team_h, fixture)] = row.team_h_difficulty
                self._team_diff[(row.team_a, fixture)] = row.team_a_difficulty

        #########################################################
        #                  Player Related Data
        #########################################################

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

        # Player ID -> Expected Points in previous weeks
        self._player_previous_xp = {}

        for gw in PAST_GWS:
            for pid in self._player_ids:
                xp_csv = xp_data_dict[gw]
                xp = xp_csv[xp_csv.id == pid].xP.values

                if len(xp):
                    self._player_previous_xp[(pid, gw)] = float(xp)
                else:
                    self._player_previous_xp[(pid, gw)] = 0

        # Add XP for future 5 weeks using regression
        self._player_future_xp = {}

        for gw in FUTURE_GWS:
            for pid in self._player_ids:
                future_xp = regression([self._player_previous_xp[(pid, gw)] for gw in PAST_GWS])
                self._player_future_xp[(pid, gw)] = future_xp[gw - CURRENT_GW]

        # Player ID -> Position
        self._player_position = {player_id: pos for player_id, pos in zip(player_data["id"], player_data["element_type"])}

        # Fixture Difficulty next week
        self._player_fixture_difficulty = {}
        for pid in self._player_ids:
            team_id = self._player_team_id[pid]
            for gw in FUTURE_GWS:
                self._player_fixture_difficulty[(pid, gw)] = self._team_diff[(team_id, gw)]

        # Chance of playing this week
        self._player_chance_of_playing = dict(zip(player_data["id"], player_data["chance_of_playing_this_round"]))
