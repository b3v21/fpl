from termcolor import colored


class Team:
    def __init__(self, id, code, short_name, long_name, difficulty):
        self._id = id
        self._code = code
        self._short_name = short_name
        self._long_name = long_name
        self._difficulty = difficulty

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, value):
        self._code = value

    @property
    def short_name(self):
        return self._short_name

    @short_name.setter
    def short_name(self, value):
        self._short_name = value

    @property
    def long_name(self):
        return self._long_name

    @long_name.setter
    def long_name(self, value):
        self._long_name = value

    @property
    def difficulty(self):
        return self._difficulty

    @difficulty.setter
    def difficulty(self, value):
        self._difficulty = value

    def get_diff_colored_name(self):
        if self.difficulty == 1:
            return colored(self._short_name, (139, 195, 74))
        elif self.difficulty == 2:
            return colored(self._short_name, (76, 175, 80))
        elif self.difficulty == 3:
            return colored(self._short_name, (255, 193, 7))
        elif self.difficulty == 4:
            return colored(self._short_name, (255, 152, 0))
        elif self.difficulty == 5:
            return colored(self._short_name, (244, 67, 54))

    def __str__(self):
        return self.get_diff_colored_name()

    def __repr__(self):
        return self.get_diff_colored_name()
