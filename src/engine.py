#!/usr/bin/env python3

from ortools.init.python import init
from ortools.sat.python import cp_model
from lib.dataloader import Dataloader
from constants import DECAY, FUTURE_GWS, CURRENT_GW, ATT, MID, DEF, GK, SEASON_HALF_GW, FUTURE_GWS_WITHOUT_CURR
from lib.solution import Solution
from lib.player import Player

# TODO LIST:
#
# MODEL IS WAY TOO SENSITIVE TO RECENT PERFORMANCES - FIX THIS
#
# INCLUDE PREVIOUS SEASON DATA IN THE MODEL - CURRENTLY THE MODEL IS USELESS IF ITS RAN WITH CURRENT_GW
# SET TO ANYTHING LESS THAN ABOUT 5 AS IT ONLY DRAWS ON THIS YEARS DATA
#
# LOOK FOR SPEED UPS IN THE MODEL, IT IS TOO SLOW WHEN RAN FOR THE WHOLE SEASON
#
# USE XGBOOST OR SIMILAR TO PREDICT PLAYER XP IN FUTURE GWS BEYOND NEXT, MAYBE USE SOME KIND OF RECURRENT MODEL


def run_engine():
    print("Google OR-Tools version:", init.OrToolsVersion.version_string())

    # Create the model and solver with the CP-SAT backend.
    model = cp_model.CpModel()
    if not model:
        print("Could not create modal CP-SAT")
        return

    solver = cp_model.CpSolver()
    if not solver:
        print("Could not create solver CP-SAT")
        return

    # Fetch data from dataloader singleton
    DL = Dataloader()
    players = DL.players
    pids = players.keys()

    print("Building Variables...")
    x = {(pid, gw): model.new_int_var(0, 1, f"x_{pid}_{gw}") for pid in pids for gw in FUTURE_GWS}
    y = {(pid, gw): model.new_int_var(0, 1, f"y_{pid}-{gw}") for pid in pids for gw in FUTURE_GWS}
    t = {(pid, gw): model.new_int_var(0, 1, f"t_{pid}_{gw}") for pid in pids for gw in FUTURE_GWS_WITHOUT_CURR}
    c = {(pid, gw): model.new_int_var(0, 1, f"c_{pid}_{gw}") for pid in pids for gw in FUTURE_GWS}
    b = {(pid, gw): model.new_int_var(0, 1, f"b_{pid}_{gw}") for pid in pids for gw in FUTURE_GWS}

    # CHIPS
    wc = {gw: model.new_int_var(0, 15, f"wc_{gw}") for gw in FUTURE_GWS_WITHOUT_CURR}  # wildcard transfers
    wc_used = {gw: model.new_bool_var(f"wc_used_{gw}") for gw in FUTURE_GWS_WITHOUT_CURR}  # wildcard used

    fh = {gw: model.new_int_var(0, 15, f"fh_{gw}") for gw in FUTURE_GWS_WITHOUT_CURR}  # free hit transfers
    fh_used = {gw: model.new_bool_var(f"fh_used_{gw}") for gw in FUTURE_GWS_WITHOUT_CURR}  # free hit used

    tc = {(pid, gw): model.new_int_var(0, 1, f"tc_{gw}") for pid in pids for gw in FUTURE_GWS}  # triple captain
    tc_used = {gw: model.new_bool_var(f"tc_used_{gw}") for gw in FUTURE_GWS}  # triple cap used

    bb_used = {gw: model.new_bool_var(f"bb_used_{gw}") for gw in FUTURE_GWS}  # bench boost used

    # aux variable for deciding whether or not a player receives BB points in a gw or not
    bench_boost_points = {(pid, gw): model.new_bool_var(name=f"bb_points_{pid}_{gw}") for pid in pids for gw in FUTURE_GWS}

    var = [x, y, t, wc, wc_used, fh, fh_used, tc, tc_used, bb_used, c, b, bench_boost_points]

    print(sum([len(v) for v in var]), "variables created.")

    model = build_constraints(model, var)

    # OBJECTIVE FUNCTION
    model.maximize(
        sum(y[(pid, gw)] * decay(gw) * players[pid].future_xp[gw] for pid in pids for gw in FUTURE_GWS)  # standard player xp
        + sum(c[(pid, gw)] * decay(gw) * players[pid].future_xp[gw] for pid in pids for gw in FUTURE_GWS)  # captain extra xp
        + sum(tc[(pid, gw)] * decay(gw) * players[pid].future_xp[gw] for pid in pids for gw in FUTURE_GWS)  # triple cap extra xp
        + sum(bench_boost_points[(pid, gw)] * decay(gw) * players[pid].future_xp[gw] for pid in pids for gw in FUTURE_GWS)  # bench boost extra xp
    )

    solve(model, solver, var)


def decay(gw):
    return DECAY ** (gw + 1 - CURRENT_GW)


def build_constraints(model, var):
    print("\nBuilding Constraints...")
    x, y, t, wc, wc_used, fh, fh_used, tc, tc_used, bb_used, c, b, bench_boost_points = var

    # Fetch data from dataloader singleton
    DL = Dataloader()
    players: dict[int, Player] = DL.players
    pids = players.keys()

    # cost constraint
    for gw in FUTURE_GWS:
        model.add(cp_model.LinearExpr.sum([players[pid].price * x[(pid, gw)] for pid in pids]) <= 1000)

    # we generally want to have most of our money in the team, this should remove a bunch of solutions
    for gw in FUTURE_GWS:
        model.add(cp_model.LinearExpr.sum([players[pid].price * x[(pid, gw)] for pid in pids]) >= 950)

    # number of players in squad constraint
    for gw in FUTURE_GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, gw)] for pid in pids]) == 15)

    # 2 GKs allowed
    for gw in FUTURE_GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, gw)] for pid in pids if players[pid].position == GK]) == 2)

    # 5 DEFs allowed
    for gw in FUTURE_GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, gw)] for pid in pids if players[pid].position == DEF]) == 5)

    # 5 MIDs allowed
    for gw in FUTURE_GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, gw)] for pid in pids if players[pid].position == MID]) == 5)

    # 3 ATTs allowed
    for gw in FUTURE_GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, gw)] for pid in pids if players[pid].position == ATT]) == 3)

    # 1 GK on the field
    for gw in FUTURE_GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids if players[pid].position == GK]) == 1)

    # 3-5 DEFs on the field
    for gw in FUTURE_GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids if players[pid].position == DEF]) >= 3)
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids if players[pid].position == DEF]) <= 5)

    # 2-5 MIDs on the field
    for gw in FUTURE_GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids if players[pid].position == MID]) >= 2)
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids if players[pid].position == MID]) <= 5)

    # 1-3 ATTs on the field
    for gw in FUTURE_GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids if players[pid].position == ATT]) >= 1)
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids if players[pid].position == ATT]) <= 3)

    # max 3 players per team
    for gw in FUTURE_GWS:
        for team in DL.teams.keys():
            model.add(cp_model.LinearExpr.sum([x[(pid, gw)] for pid in pids if players[pid].team.id == team]) <= 3)

    # max 11 players on the field
    for gw in FUTURE_GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids]) == 11)

    # a player must be in the team in order to be on the field
    for pid in pids:
        for gw in FUTURE_GWS:
            model.add(y[(pid, gw)] <= x[(pid, gw)])

    # don't play any players that are potentially injured / dont exist
    for pid in pids:
        for gw in FUTURE_GWS:
            if players[pid].chance_of_playing < 75:
                model.add(y[(pid, gw)] == 0)

    # only 1 captain per week
    for gw in FUTURE_GWS:
        model.add(cp_model.LinearExpr.sum([c[(pid, gw)] for pid in pids]) == 1)

    # captain must be on the field
    for pid in pids:
        for gw in FUTURE_GWS:
            model.add(c[(pid, gw)] <= y[(pid, gw)])

    # link b (benched players) and x (in the squad)
    for gw in FUTURE_GWS:
        for pid in pids:
            model.add(x[(pid, gw)] - y[(pid, gw)] == b[(pid, gw)])

    ################################################### Transfer constraints ######################################################

    for gw in FUTURE_GWS_WITHOUT_CURR:
        for pid in pids:
            # t ≥ |x1 - x2| (make t detect a transfer)
            model.add(t[(pid, gw)] >= x[(pid, gw)] - x[(pid, gw - 1)])
            model.add(t[(pid, gw)] >= x[(pid, gw - 1)] - x[(pid, gw)])

            model.add(t[(pid, gw)] <= x[(pid, gw)] + x[(pid, gw - 1)])
            model.add(t[(pid, gw)] <= 2 - x[(pid, gw)] - x[(pid, gw - 1)])

        # transfers available this GW (assuming NONE have been used all season)
        trans_this_gw = 2 * (gw - CURRENT_GW)

        # transfers already made this season
        trans_made = cp_model.LinearExpr.sum([t[(p, past_gw)] for p in pids for past_gw in FUTURE_GWS_WITHOUT_CURR if past_gw < gw])

        # transfers via wildcard used in previous gws
        wildcard_trans_used = 2 * cp_model.LinearExpr.sum([wc[past_gw] for past_gw in FUTURE_GWS_WITHOUT_CURR if past_gw < gw])

        # can only make the number of transfers available (1 transfer (2 players) per GW by default but can bank and use later)
        model.add(
            cp_model.LinearExpr.sum([t[(pid, gw)] for pid in pids]) <= (trans_this_gw - trans_made + wildcard_trans_used)
        ).only_enforce_if(~wc_used[gw]).only_enforce_if(~fh_used[gw])

    # can only make len(GWS) + wc transfers + fh transfers across the whole season
    model.add(
        cp_model.LinearExpr.sum([t[(pid, gw)] for pid in pids for gw in FUTURE_GWS_WITHOUT_CURR])
        <= (2 * len(FUTURE_GWS_WITHOUT_CURR))  # standard transfers
        + (2 * cp_model.LinearExpr.sum([wc[gw] for gw in FUTURE_GWS_WITHOUT_CURR]))  # wc
        + (4 * cp_model.LinearExpr.sum([fh[gw] for gw in FUTURE_GWS_WITHOUT_CURR]))  # fh
    )

    # no two chips can be used in the same gw
    for gw in FUTURE_GWS_WITHOUT_CURR:
        model.add(wc_used[gw] + fh_used[gw] + bb_used[gw] + tc_used[gw] <= 1)
    for gw in FUTURE_GWS:
        model.add(bb_used[gw] + tc_used[gw] <= 1)  # only bb and tc can be used in starting gw

    ################################################### Wild Card constraints ######################################################

    # wildcard var link to transfer var
    for gw in FUTURE_GWS_WITHOUT_CURR:
        # if wildcard is used, turn on wc_used boolean so we can selectively enforce wildcard transfer constraints
        # if wc used, we always want > 1 transfer, otherwise standard transfers couldve been used
        model.add(wc[gw] > 1).only_enforce_if(wc_used[gw])
        model.add(wc[gw] == 0).only_enforce_if(~wc_used[gw])

        # x2 as each transfer involves 2 players
        model.add(2 * wc[gw] == cp_model.LinearExpr.sum([t[(pid, gw)] for pid in pids])).only_enforce_if(wc_used[gw])

    # WC chips can be used once before GW 19 and once after GW 19
    model.add(cp_model.LinearExpr.sum([wc_used[gw] for gw in FUTURE_GWS_WITHOUT_CURR if gw <= SEASON_HALF_GW]) <= 1)
    model.add(cp_model.LinearExpr.sum([wc_used[gw] for gw in FUTURE_GWS_WITHOUT_CURR if gw > SEASON_HALF_GW]) <= 1)

    ################################################### Free Hit constraints ######################################################

    # free hit var link to transfer var
    for gw in FUTURE_GWS_WITHOUT_CURR:
        # if freehit is used, turn on fh_used boolean so we can selectively enforce freehit transfer constraints
        # if fh used, we always want > 1 transfer, otherwise standard transfers couldve been used
        model.add(fh[gw] > 1).only_enforce_if(fh_used[gw])
        model.add(fh[gw] == 0).only_enforce_if(~fh_used[gw])

        # x2 as each transfer involves 2 players
        model.add(2 * fh[gw] == cp_model.LinearExpr.sum([t[(pid, gw)] for pid in pids])).only_enforce_if(fh_used[gw])

        if gw + 1 in FUTURE_GWS:
            # After FH we need to go back to old team, so need to be able to 'transfer' back (unless WC is played afterwards)
            model.add(2 * fh[gw] == cp_model.LinearExpr.sum([t[(pid, gw + 1)] for pid in pids])).only_enforce_if(
                fh_used[gw]
            ).only_enforce_if(~wc_used[gw + 1])

    # FH chips can be used once before GW 19 and once after GW 19
    model.add(cp_model.LinearExpr.sum([fh_used[gw] for gw in FUTURE_GWS_WITHOUT_CURR if gw <= SEASON_HALF_GW]) <= 1)
    model.add(cp_model.LinearExpr.sum([fh_used[gw] for gw in FUTURE_GWS_WITHOUT_CURR if gw > SEASON_HALF_GW]) <= 1)

    # cant use free hit in last GW
    model.add(fh_used[max(FUTURE_GWS)] == 0)

    # After Free Hit, team returns to how it was before, unless a WC is played next week
    for gw in FUTURE_GWS_WITHOUT_CURR:
        if gw + 1 in FUTURE_GWS:
            for pid in pids:
                model.add(x[(pid, gw + 1)] == x[(pid, gw - 1)]).only_enforce_if(fh_used[gw]).only_enforce_if(~wc_used[gw + 1])

    ################################################### Triple Captain constraints ################################################

    # TC can be used once before GW 19 and once after GW 19
    model.add(cp_model.LinearExpr.sum([tc_used[gw] for gw in FUTURE_GWS if gw <= SEASON_HALF_GW]) <= 1)
    model.add(cp_model.LinearExpr.sum([tc_used[gw] for gw in FUTURE_GWS if gw > SEASON_HALF_GW]) <= 1)

    # if tc is used, turn on tc_used boolean
    for gw in FUTURE_GWS:
        model.add(sum([tc[(pid, gw)] for pid in pids]) == 1).only_enforce_if(tc_used[gw])
        model.add(sum([tc[(pid, gw)] for pid in pids]) == 0).only_enforce_if(~tc_used[gw])

    # triple captain and captain link
    for gw in FUTURE_GWS:
        for pid in pids:
            model.add(tc[(pid, gw)] == c[(pid, gw)]).only_enforce_if(tc_used[gw])

    ################################################### Bench Boost constraints ###################################################

    # BB can be used once before GW 19 and once after GW 19
    model.add(cp_model.LinearExpr.sum([bb_used[gw] for gw in FUTURE_GWS if gw <= SEASON_HALF_GW]) <= 1)
    model.add(cp_model.LinearExpr.sum([bb_used[gw] for gw in FUTURE_GWS if gw > SEASON_HALF_GW]) <= 1)

    for pid in pids:
        for gw in FUTURE_GWS:
            model.add(bench_boost_points[(pid, gw)] <= b[(pid, gw)])
            model.add(bench_boost_points[(pid, gw)] <= bb_used[gw])
            model.add(bench_boost_points[(pid, gw)] >= b[(pid, gw)] + bb_used[gw] - 1)

    ###############################################################################################################################

    print(len(model.Proto().constraints), "constraints added.")
    return model


def solve(model, solver, var):
    print("\nSolving...")
    status = solver.solve(model)

    if status:
        sol = Solution(var, status, solver)
        print(sol)
    else:
        print("\nNo Solution Found")

    print("\nStatistics:")
    print(f"status    - {solver.status_name(status)}")
    print(f"conflicts - {solver.num_conflicts}")
    print(f"branches  - {solver.num_branches}")
    print(f"wall time - {round(solver.wall_time)} seconds\n")


if __name__ == "__main__":
    run_engine()
