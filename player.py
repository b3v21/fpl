from team import Team


class Player:
    def __init__(self, id, price, name, team, position, chance_of_playing, vs_team_id, vs_team_diff, prev_xp, future_xp):
        self._id = id
        self._price = price
        self._name = name
        self._team: Team = team
        self._position = position
        self._chance_of_playing = chance_of_playing

        self._vs_team_id = vs_team_id
        self._vs_team_diff = vs_team_diff
        self._prev_xp = prev_xp
        self._future_xp = future_xp

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, value):
        self._price = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def team(self):
        return self._team

    @team.setter
    def team(self, value):
        self._team = value

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        self._position = value

    @property
    def chance_of_playing(self):
        return self._chance_of_playing

    @chance_of_playing.setter
    def chance_of_playing(self, value):
        self._chance_of_playing = value

    @property
    def vs_team_id(self):
        return self._vs_team_id

    @vs_team_id.setter
    def vs_team_id(self, value):
        self._vs_team_id = value

    @property
    def vs_team_diff(self):
        return self._vs_team_diff

    @vs_team_diff.setter
    def vs_team_diff(self, value):
        self._vs_team_diff = value

    @property
    def prev_xp(self):
        return self._prev_xp

    @prev_xp.setter
    def prev_xp(self, value):
        self._prev_xp = value

    @property
    def future_xp(self):
        return self._future_xp

    @future_xp.setter
    def future_xp(self, value):
        self._future_xp = value
