#!/usr/bin/env python3

from ortools.init.python import init
from ortools.sat.python import cp_model
from dataloader import Dataloader, GWS, CURRENT_GW, SIMPLE

GK = 1
DEF = 2
MID = 3
ATT = 4

POS_LOOKUP = {GK: "GK", DEF: "DEF", MID: "MID", ATT: "ATT"}
DASH = "-"
SEASON_HALF_GW = 19  # GW where the season half's change
MAX_TRANSFERS = 15  # max possible in a GW (if wildcard or free hit used)


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
    DL = Dataloader(SIMPLE)
    players = DL.players
    pids = players.keys()

    print("Building Variables...")
    x = {(pid, gw): model.new_int_var(0, 1, f"x_{pid}") for pid in pids for gw in GWS}
    y = {(pid, gw): model.new_int_var(0, 1, f"y_{pid}") for pid in pids for gw in GWS}
    t = {(pid, gw): model.new_int_var(0, 1, f"diff_{pid}_{gw}") for pid in pids for gw in GWS if gw > CURRENT_GW}

    # CHIPS
    wc = {gw: model.new_int_var(0, 15, f"wc_{gw}") for gw in GWS if gw > CURRENT_GW}  # wildcard transfers
    wc_used = {gw: model.new_bool_var(f"wc_used_{gw}") for gw in GWS if gw > CURRENT_GW}  # wildcard used

    fh = {gw: model.new_int_var(0, 1, f"fh_{gw}") for gw in GWS if gw > CURRENT_GW}  # free hit
    tc = {gw: model.new_int_var(0, 1, f"tc_{gw}") for gw in GWS if gw > CURRENT_GW}  # triple captain
    bb = {gw: model.new_int_var(0, 1, f"bb_{gw}") for gw in GWS if gw > CURRENT_GW}  # bench boost

    var = [x, y, t, wc, wc_used, fh, tc, bb]

    print(sum([len(v) for v in var]), "variables created.")

    model = build_constraints(model, var)

    # OBJECTIVE FUNCTION
    model.maximize(
        sum(y[(pid, gw)] * players[pid].xp[gw] for pid in pids for gw in GWS)
        + sum(y[(pid, gw)] * (3 * (3 - players[pid].vs_team_diff[gw])) for pid in pids for gw in GWS)
    )
    # in this niave model, a fixture difficultly of '1' gives the player an XP of +2, '2' is +1, '3' is 0, '4' is -1 and '5' is -2,
    # this is done via the linear function 3 - DF. This is then multipled by 3 to give it more weight in the objective function.

    solve(model, solver, var)


def build_constraints(model, var):
    print("\nBuilding Constraints...")
    x, y, t, wc, wc_used, fh, tc, bb = var

    # Fetch data from dataloader singleton
    DL = Dataloader()
    players = DL.players
    pids = players.keys()

    # cost constraint
    for gw in GWS:
        model.add(cp_model.LinearExpr.sum([players[pid].price * x[(pid, gw)] for pid in pids]) <= 1000)

    if not SIMPLE:
        # we generally want to have most of our money in the team, this should remove a bunch of solutions
        for gw in GWS:
            model.add(cp_model.LinearExpr.sum([players[pid].price * x[(pid, gw)] for pid in pids]) >= 950)

    # number of players in squad constraint
    for gw in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, gw)] for pid in pids]) == 15)

    # 2 GKs allowed
    for gw in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, gw)] for pid in pids if players[pid].position == GK]) == 2)

    # 5 DEFs allowed
    for gw in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, gw)] for pid in pids if players[pid].position == DEF]) == 5)

    # 5 MIDs allowed
    for gw in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, gw)] for pid in pids if players[pid].position == MID]) == 5)

    # 3 ATTs allowed
    for gw in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, gw)] for pid in pids if players[pid].position == ATT]) == 3)

    # 1 GK on the field
    for gw in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids if players[pid].position == GK]) == 1)

    # 3-5 DEFs on the field
    for gw in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids if players[pid].position == DEF]) >= 3)
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids if players[pid].position == DEF]) <= 5)

    # 2-5 MIDs on the field
    for gw in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids if players[pid].position == MID]) >= 2)
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids if players[pid].position == MID]) <= 5)

    # 1-3 ATTs on the field
    for gw in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids if players[pid].position == ATT]) >= 1)
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids if players[pid].position == ATT]) <= 3)

    # # max 3 players per team
    for gw in GWS:
        for team_code in DL.team_code_name.keys():
            model.add(cp_model.LinearExpr.sum([x[(pid, gw)] for pid in pids if players[pid].team_code == team_code]) <= 3)

    # max 11 players on the field
    for gw in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, gw)] for pid in pids]) == 11)

    # a player must be in the team in order to be on the field
    for pid in pids:
        for gw in GWS:
            model.add(y[(pid, gw)] <= x[(pid, gw)])

    ########### Transfer constraints ###########

    for gw in GWS:
        if gw > CURRENT_GW:
            for pid in pids:
                model.add(t[(pid, gw)] >= x[(pid, gw)] - x[(pid, gw - 1)])
                model.add(t[(pid, gw)] >= x[(pid, gw - 1)] - x[(pid, gw)])
                model.add(t[(pid, gw)] <= x[(pid, gw - 1)] + x[(pid, gw)])

            # transfers available this GW (assuming NONE have been used all season)
            trans_this_gw = 2 * (gw - CURRENT_GW)

            # transfers already made this season
            trans_made = cp_model.LinearExpr.sum(
                [t[(p, past_gw)] for p in pids for past_gw in GWS if past_gw < gw and past_gw != CURRENT_GW]
            )

            # transfers via wildcard used in previous gws
            wildcard_trans_used = 2 * cp_model.LinearExpr.sum([wc[past_gw] for past_gw in GWS if past_gw < gw and past_gw != CURRENT_GW])

            # can only make the number of transfers available (1 transfer (2 players) per GW by default but can bank and use later)
            model.add(
                cp_model.LinearExpr.sum([t[(pid, gw)] for pid in pids]) <= (trans_this_gw - trans_made + wildcard_trans_used)
            ).only_enforce_if(~wc_used[gw])

    # can only make len(GWS) + wc transfers across the whole season
    model.add(
        cp_model.LinearExpr.sum([t[(pid, gw)] for pid in pids for gw in GWS if gw > CURRENT_GW])
        <= (2 * len(GWS)) + (2 * cp_model.LinearExpr.sum([wc[gw] for gw in GWS if gw > CURRENT_GW]))
    )

    ########### Chip constraints ###########

    # wildcard var link to transfer var
    for gw in GWS:
        if gw > CURRENT_GW:
            # if wildcard is used, turn on wc_used boolean so we can selectively enforce wildcard transfer constraints
            # if wc used, we always want > 1 transfer, otherwise standard transfers couldve been used
            model.add(wc[gw] > 1).only_enforce_if(wc_used[gw])
            model.add(wc[gw] <= 0).only_enforce_if(~wc_used[gw])

            # x2 as each transfer involves 2 players
            model.add(2 * wc[gw] == cp_model.LinearExpr.sum([t[(pid, gw)] for pid in pids])).only_enforce_if(wc_used[gw])

    # All chips can be used only before GW 19 and once after GW 19
    model.add(cp_model.LinearExpr.sum([wc_used[gw] for gw in GWS if gw > CURRENT_GW and gw <= SEASON_HALF_GW]) <= 1)
    # model.add(cp_model.LinearExpr.sum([fh[gw] for gw in GWS if gw > CURRENT_GW and gw <= SEASON_HALF_GW]) == 1)
    # model.add(cp_model.LinearExpr.sum([tc[gw] for gw in GWS if gw > CURRENT_GW and gw <= SEASON_HALF_GW]) == 1)
    # model.add(cp_model.LinearExpr.sum([bb[gw] for gw in GWS if gw > CURRENT_GW and gw <= SEASON_HALF_GW]) == 1)

    model.add(cp_model.LinearExpr.sum([wc_used[gw] for gw in GWS if gw > CURRENT_GW and gw > SEASON_HALF_GW]) <= 1)
    # model.add(cp_model.LinearExpr.sum([fh[gw] for gw in GWS if gw > CURRENT_GW and gw > SEASON_HALF_GW]) == 1)
    # model.add(cp_model.LinearExpr.sum([tc[gw] for gw in GWS if gw > CURRENT_GW and gw > SEASON_HALF_GW]) == 1)
    # model.add(cp_model.LinearExpr.sum([bb[gw] for gw in GWS if gw > CURRENT_GW and gw > SEASON_HALF_GW]) == 1)

    # don't play any players that are potentially injured / dont exist
    for pid in pids:
        for gw in GWS:
            if players[pid].chance_of_playing < 75:
                model.add(y[(pid, gw)] == 0)

    print(len(model.Proto().constraints), "constraints added.")
    return model


def solve(model, solver, var):
    print("\nSolving...")
    status = solver.solve(model)

    # Fetch data from dataloader singleton
    DL = Dataloader()
    players = DL.players

    # unpack vars
    x, y, t, wc, wc_used, fh, tc, bb = var

    transfer_count = {}
    wildcards = {}

    print(f"Status: {status}")
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        results: list[Player] = {}

        # Collect results
        for [(id, gw), x_val] in x.items():
            if solver.value(x_val):
                if results.get(gw):
                    results[gw] += [players[id]]
                else:
                    results[gw] = [players[id]]

        # Collect WC Usage
        for [gw, val] in wc.items():
            if solver.value(val):
                wildcards[gw] = solver.value(val)

        # Display
        for gw in reversed(GWS):
            total_cost = 0
            print(DASH * 80)
            print(f"GAMEWEEK {gw}")
            if gw > CURRENT_GW:
                print("\nTransfers:")
                for p1 in [p for (p, g), val in x.items() if g == gw and (solver.value(val) - solver.value(x[(p, g - 1)])) == 1]:
                    print("IN:", f"({POS_LOOKUP[players[p1].position]})", players[p1].name, f"(£{players[p1].price / 10})")
                    transfer_count[gw] = transfer_count.get(gw, 0) + 1
                print("")
                for p2 in [p for (p, g), val in x.items() if g == gw and (solver.value(x[(p, g - 1)]) - solver.value(val)) == 1]:
                    print("OUT:", f"({POS_LOOKUP[players[p2].position]})", players[p2].name, f"(£{players[p2].price / 10})")
            print(DASH * 80)
            for pos_value, pos_name in POS_LOOKUP.items():  # for each position, find all players for this GW
                print(f"{pos_name}:")
                for p in [r for r in results[gw] if r.position == pos_value]:
                    total_cost += p.price / 10
                    playing = " - PLAYING" if solver.value(y[(p.id, gw)]) else ""
                    vs = DL.team_code_name[DL.team_id_team_code[p._vs_team_id[gw]]]

                    print(f"({p.team_name}) {p.name} ({p.id}) (price: {p.price / 10}) vs ({vs})" + playing)

                print("")

            print("Team Value: " + str(round(total_cost, 1)))
            print("Money in Bank: " + str(round(100 - total_cost, 1)))
            print("")

        print(DASH * 80)

    else:
        print("No solution found.")

    print("\nStatistics:")
    print("")
    print(f"status    - {solver.status_name(status)}")
    print(f"conflicts - {solver.num_conflicts}")
    print(f"branches  - {solver.num_branches}")
    print(f"wall time - {solver.wall_time} s\n")
    print(f"Maximum of objective function: {round(solver.objective_value)} ({round(solver.objective_value / len(GWS))} per GW)")
    print(
        f"Total Transfers: {sum(transfer_count.values()) - sum(wildcards.values())} ({len(GWS) - 1 - sum(transfer_count.values()) + sum(wildcards.values())} left over)"
    )
    print(f"\nTransfers per GW:")
    for gw in GWS:
        if gw > CURRENT_GW:
            if gw in wildcards.keys():
                print(f"GW {gw}: WILDCARD USED ({wildcards[gw]} transfers)")
            else:
                print(f"GW {gw}: {transfer_count.get(gw, 'ROLL')}")

    print("")
    print("Wild Card used in: ")
    for gw, t in wildcards.items():
        print(f"GAMEWEEK {gw} ({t} transfers)")
    print("")


def main():
    run_engine()


if __name__ == "__main__":
    main()
