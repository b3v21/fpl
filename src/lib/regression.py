import numpy as np
from sklearn.linear_model import LinearRegression
from src.constants import CURRENT_GW, FUTURE_GWS


def regression(previous_xp: list[float]):
    x = np.arange(1, CURRENT_GW).reshape(-1, 1)  # features must be 2D
    y = np.array(previous_xp)

    model = LinearRegression()
    model.fit(x, y)

    x_new = np.array([[x] for x in FUTURE_GWS])
    y_pred = model.predict(x_new)

    res = list(map(lambda x: round(float(x), 1), y_pred))

    return res
