import pandas as pd
import numpy as np
from .player import Player
import xgboost as xgb
from constants import PAST_GWS, CURRENT_GW


##### IDEA #####
# Use XGBoost to predict the xp for next week based on prior data
# (we train the model to predict points for week 'x' based on week x-1 data)
#
# We can then use the model to predict the points for the next gw (any potentially a few gws ahead)

NAME = ["name"]
GW_COL = ["GW"]
FEATURES = [
    "xP",
    "team",
    "position",
    "bps",
    "minutes",
    "ict_index",
    "yellow_cards",
    "red_cards",
    "selected",
    "starts",
    "transfers_in",
    "transfers_out",
    "value",
]
FUTURE_FEATURES = ["opponent_team", "was_home", "total_points"]
COMPUTED_FEATURES = ["opp_next", "is_home_next", "points_rolling_avg_3", "points_rolling_avg_5", "season_total_points", "minutes_avg"]
ALL_FEATURES = list(set(FEATURES + FUTURE_FEATURES))
TARGET = ["points_next"]

pd.set_option("display.max_columns", None)


def train_model(df: pd.DataFrame, players: list[Player]):
    df["position"] = df["position"].astype("category")
    df["team"] = df["team"].astype("category")
    df["name"] = df["name"].astype("category")
    df["was_home"] = df["was_home"].astype("category")

    # Create global df to put all training rows into
    all_data = pd.DataFrame()

    # filter duplicate rows for the player
    df = df.drop_duplicates(subset=["name", "GW"], keep="last")

    for player in players:
        # need to include name and gw column for filtering
        rows = df[(df.name == player.name)][NAME + ALL_FEATURES + GW_COL]

        for gw in PAST_GWS:
            curr_gw = rows[rows["GW"] == gw].copy()

            # add rolling average features
            if gw > 3:
                past_3 = rows[rows["GW"] < gw].tail(3)
                curr_gw["points_rolling_avg_3"] = np.mean(past_3["total_points"])
            if gw > 5:
                past_5 = rows[rows["GW"] < gw].tail(5)
                curr_gw["points_rolling_avg_5"] = np.mean(past_5["total_points"])

            # add season cumulative points feature
            cum_points = rows[rows["GW"] < gw]
            curr_gw["season_total_points"] = np.sum(cum_points["total_points"])

            # add season minutes played avg feature
            if gw > 1:
                minutes_avg = rows[rows["GW"] < gw]
                curr_gw["minutes_avg"] = np.mean(minutes_avg["minutes"])

            if gw + 1 < CURRENT_GW:  # can only get future data from the week before NOW and earlier
                next_gw = rows[rows["GW"] == (gw + 1)][NAME + FUTURE_FEATURES].copy()
                next_gw = next_gw.rename(columns={"total_points": "points_next", "opponent_team": "opp_next", "was_home": "is_home_next"})

            # Merge data from previous weeks with total_points for the current week
            result = pd.merge(curr_gw, next_gw, on="name", how="left")

            all_data = pd.concat([all_data, result])

    training_data = all_data[ALL_FEATURES + COMPUTED_FEATURES]
    target = all_data[TARGET]

    dtrain = xgb.DMatrix(training_data, label=target, enable_categorical=True)

    param = {"max_depth": 6, "eta": 0.5, "objective": "reg:squarederror"}
    bst = xgb.train(param, dtrain)

    return (bst, len(all_data))


def predict(model, players: list[Player], df: pd.DataFrame):
    for player in players:

        # filter duplicate rows for the player
        df = df.drop_duplicates(subset=["name", "GW"], keep="last")

        # include name for joining with future data
        curr_row = df[(df.name == player.name) & (df.GW == CURRENT_GW - 1)][ALL_FEATURES + NAME]

        computed_data = pd.DataFrame(
            {
                "name": [player.name],
                "opp_next": [player.get_vs_gw(CURRENT_GW).id],
                "is_home_next": [player.is_home_gw(CURRENT_GW)],
                "points_rolling_avg_3": [np.mean([df[(df.name == player.name) & (df.GW < CURRENT_GW)].tail(3)["total_points"]])],
                "points_rolling_avg_5": [np.mean([df[(df.name == player.name) & (df.GW < CURRENT_GW)].tail(5)["total_points"]])],
                "season_total_points": [np.sum(df[(df.name == player.name) & (df.GW < CURRENT_GW)]["total_points"])],
                "minutes_avg": [np.mean(df[(df.name == player.name) & (df.GW < CURRENT_GW)]["minutes"])],
            }
        )

        data = pd.merge(curr_row, computed_data, on="name", how="left")

        data["team"] = data["team"].astype("category")
        data["was_home"] = data["was_home"].astype("category")
        data["is_home_next"] = data["is_home_next"].astype("category")

        # drop name as we dont want to include it as a training feature
        data = data.drop(columns=NAME)

        dtest = xgb.DMatrix(data, enable_categorical=True)
        ypred = model.predict(dtest)

        player.set_future_xp(CURRENT_GW, ypred[0])
