from .team import Team
from .fixture import Fixture
from constants import FUTURE_GWS


class Player:
    def __init__(self, id, metadata, team, fixtures):
        self._id = id
        self._metadata = metadata
        self._team: Team = team
        self._fixtures: dict[int, Fixture] = fixtures

    def get_vs_gw(self, gw):
        fixture = self.fixtures[gw]

        if self.team == fixture.team_a:
            return fixture.team_h
        else:
            return fixture.team_a

    def get_fixture_diff(self, gw):
        return self.get_vs_gw(gw).difficulty

    def load_future_data():
        return

    def __str__(self):
        return self.name

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def name(self):
        return f"{self._metadata['first_name'].values[0]} {self._metadata['second_name'].values[0]}"

    @property
    def price(self):
        return self._metadata["now_cost"].values[0]

    @property
    def position(self):
        return self._metadata["element_type"].values[0]

    @property
    def chance_of_playing(self):
        return self._metadata["chance_of_playing_this_round"].values[0]

    @property
    def future_xp(self):
        return {gw: self._metadata['ep_next'].values[0] for gw in FUTURE_GWS}  # TODO: attach to supervised learning model

    @property
    def fixtures(self):
        return self._fixtures

    @property
    def team(self):
        return self._team

    @team.setter
    def team(self, value):
        self._team = value
