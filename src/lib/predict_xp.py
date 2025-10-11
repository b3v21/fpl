import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier


##### IDEA #####
# Use XGBoost to predict the xp for next week based on prior data
# (we train the model to predict points for week 'x' based on [(week 'x')-1,start] data)
# This gives us (x-1) * (no. of players ~ 700) sets of training data PER SEASON
#
# We can then use the model to predict the points for the next gw (any potentially a few gws ahead)

# We will use the following features
#   "fpl_points_rolling_avg_3"  # Last 3 game average
#   "fpl_points_rolling_avg_5"  # Last 5 game average
#   "season_total_points"
#   "minutes_played_avg"
#   "form"  # Recent performance metric
#   "opposition_difficulty",  # 1-5 scale
#   "is_home",  # 1 for home, 0 for away
#   "position",  # Forward/Midfielder/Defender/Goalkeeper
#   "price",  # FPL price


if __name__ == "__main__":
    X_train, X_test, y_train, y_test = train_test_split(data["data"], data["target"], test_size=0.2)
    # create model instance
    bst = XGBClassifier(n_estimators=2, max_depth=2, learning_rate=1, objective="binary:logistic")
    # fit model
    bst.fit(X_train, y_train)
    # make predictions
    preds = bst.predict(X_test)
