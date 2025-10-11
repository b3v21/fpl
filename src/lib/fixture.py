class Fixture:
    def __init__(self, code, team_h, team_a, gw):
        self._code = code
        self._team_a = team_a
        self._team_h = team_h
        self._gw = gw

    def __str__(self):
        return f"{self._team_h} (h) vs {self._team_a} (a)"

    def __repr__(self):
        return f"{self._team_h} (h) vs {self._team_a} (a)"

    @property
    def gw(self):
        return self._gw

    @gw.setter
    def gw(self, value):
        self._gw = value

    @property
    def team_a(self):
        return self._team_a

    @team_a.setter
    def team_a(self, value):
        self._team_a = value

    @property
    def team_h(self):
        return self._team_h

    @team_h.setter
    def team_h(self, value):
        self._team_h = value
