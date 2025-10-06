########## MODIFY THESE CONSTANTS AS NEEDED ##########
SEASON = "2025-26"
CURRENT_GW = 1
TOTAL_GWS = 38
GW_LOOKAHEAD = None  # number of GWs to plan for, use None for all GWs

########## THESE SHOULD MOSTLY BE STATIC ##########
GWS = range(CURRENT_GW, (CURRENT_GW + GW_LOOKAHEAD + 1) if GW_LOOKAHEAD is not None else TOTAL_GWS + 1)

GK = 1
DEF = 2
MID = 3
ATT = 4

POS_LOOKUP = {GK: "GK", DEF: "DEF", MID: "MID", ATT: "ATT"}
DASH = "-"
SEASON_HALF_GW = 19  # GW where the season half's change
MAX_TRANSFERS = 15  # max possible in a GW (if wildcard or free hit used)
