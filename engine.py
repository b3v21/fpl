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

    print(len(x) + len(y) + len(t), "variables created.")

    var = [x, y, t]

    model = build_constraints(model, var)

    # OBJECTIVE FUNCTION
    model.maximize(
        sum(y[(pid, gw)] * players[pid].xp[gw] for pid in pids for gw in GWS)
        + sum(y[(pid, gw)] * (3 - players[pid].vs_team_diff[gw]) for pid in pids for gw in GWS)
    )
    # in this niave model, a fixture difficultly of '1' gives the player an XP of +2, '2' is +1, '3' is 0, '4' is -1 and '5' is -2,
    # this is done via the linear function 3 - DF

    solve(model, solver, var)


def build_constraints(model, var):
    print("\nBuilding Constraints...")
    x, y, t = var

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

    # can only make the number of transfers available (1 per GW by default but can bank and use later)
    for gw in GWS:
        if gw > CURRENT_GW:
            for pid in pids:
                model.add(t[(pid, gw)] >= x[(pid, gw)] - x[(pid, gw - 1)])
                model.add(t[(pid, gw)] >= x[(pid, gw - 1)] - x[(pid, gw)])
                model.add(t[(pid, gw)] <= x[(pid, gw - 1)] + x[(pid, gw)])

            model.add(
                cp_model.LinearExpr.sum([t[(pid, gw)] for pid in pids])
                <= (2 * (gw - 1) - cp_model.LinearExpr.sum([t[(p, past_gw)] for p in pids for past_gw in GWS if past_gw < gw and past_gw != CURRENT_GW]))
            )

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
    x, y, t = var

    transfer_count = {}

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

        # Display
        for gw in reversed(GWS):
            total_cost = 0
            print(DASH * 80)
            print(f"GAMEWEEK {gw}")
            if gw > CURRENT_GW:
                print("\nTransfers:")
                for p1 in [p for (p, g), val in x.items() if g == gw and (solver.value(val) - solver.value(x[(p, g - 1)])) == 1]:
                    print("IN:", f"({POS_LOOKUP[players[p1].position]})", players[p1].name, f"(${players[p1].price / 10})")
                    transfer_count[gw] = transfer_count.get(gw, 0) + 1
                print("")
                for p2 in [p for (p, g), val in x.items() if g == gw and (solver.value(x[(p, g - 1)]) - solver.value(val)) == 1]:
                    print("OUT:", f"({POS_LOOKUP[players[p2].position]})", players[p2].name, f"(${players[p2].price / 10})")
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
    print(f"Maximum of objective function: {round(solver.objective_value)} ({round(solver.objective_value / len(GWS))} per GW)\n")
    print(f"Total Transfers: {sum(transfer_count.values())} ({len(GWS) - sum(transfer_count.values())} left over)")
    print(f"Transfers per GW:")
    for gw in GWS:
        print(f"GW {gw}: {transfer_count.get(gw, 'BANKED')}")
    print("")
    print(f"status    - {solver.status_name(status)}")
    print(f"conflicts - {solver.num_conflicts}")
    print(f"branches  - {solver.num_branches}")
    print(f"wall time - {solver.wall_time} s\n")


def main():
    run_engine()


if __name__ == "__main__":
    main()
