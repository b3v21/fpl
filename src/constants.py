########## MODIFY THESE CONSTANTS AS NEEDED ##########
SEASON = "2025-26"
CURRENT_GW = 8
TOTAL_GWS = 38  # this cannot go above 38
FIX_DIFF_COEFF = 2 # 1-3 is a reasonable value for this
DECAY = 0.75 # decay scalar to add to future player point predictions

########## THESE SHOULD BE STATIC PENDING ANY MAJOR FPL CHANGES ##########
NEXT_GW = CURRENT_GW + 1
PAST_GWS = range(1, CURRENT_GW)
FUTURE_GWS = range(CURRENT_GW, TOTAL_GWS + 1)
FUTURE_GWS_WITHOUT_CURR = range(NEXT_GW, TOTAL_GWS + 1)

GK = 1
DEF = 2
MID = 3
ATT = 4

POS_LOOKUP = {GK: "GK", DEF: "DEF", MID: "MID", ATT: "ATT"}
DASH = "-"
SEASON_HALF_GW = 19  # GW where the season half's change
MAX_TRANSFERS = 15  # max possible in a GW (if wildcard or free hit used)
