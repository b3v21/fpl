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
    t = {
        (p1, p2, gw): model.new_int_var(0, 1, f"t_{p1}_{p2}_{gw}")
        for p1 in pids
        for p2 in pids
        for gw in GWS
        if players[p1].position == players[p2].position and p1 != p2 and gw > CURRENT_GW
    }

    print(len(t) + len(x) + len(y), "variables created.")

    var = [x, y, t]

    model = build_constraints(model, var)

    # OBJECTIVE FUNCTION
    model.maximize(
        sum(y[(pid, gw)] * players[pid].xp[gw] for pid in pids for gw in GWS)
        + sum(y[(pid, gw)] * (2 * -players[pid].vs_team_diff[gw]) for pid in pids for gw in GWS)
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

    ###############################################################################################################
    # SYSTEM OF 3 CONSTRAINTS TO MAKE SURE A TRANSFER IS TRIGGERED WHEN A PLAYER IS ADDED (/ REMOVED)
    # These are equivalent to: t = NOT x(gw-1) AND x(gw) (t = (1-x(gw-1)) * x(gw))

    # t >= x(gw) - x(gw-1)
    for p1 in pids:
        for gw in GWS:
            if gw > CURRENT_GW:
                model.add(
                    x[(p1, gw)] - x[(p1, gw - 1)]
                    <= cp_model.LinearExpr.sum(
                        [t[(p2, p1, gw)] for p2 in pids if players[p1].position == players[p2].position and p1 != p2]
                    )
                )

    # t <= x(gw)
    for p1 in pids:
        for gw in GWS:
            if gw > CURRENT_GW:
                model.add(
                    x[(p1, gw)]
                    >= cp_model.LinearExpr.sum(
                        [t[(p2, p1, gw)] for p2 in pids if players[p1].position == players[p2].position and p1 != p2]
                    )
                )

    # t <= 1 - x(gw-1)
    for p1 in pids:
        for gw in GWS:
            if gw > CURRENT_GW:
                model.add(
                    1 - x[(p1, gw - 1)]
                    >= cp_model.LinearExpr.sum(
                        [t[(p2, p1, gw)] for p2 in pids if players[p1].position == players[p2].position and p1 != p2]
                    )
                )

    ###############################################################################################################

    # a player must be in the squad if they are transferred in
    for p1 in pids:
        for p2 in pids:
            if players[p1].position == players[p2].position and p1 != p2:
                for gw in GWS:
                    if gw > CURRENT_GW:
                        model.add(t[(p1, p2, gw)] <= x[(p2, gw)])

    # a player cant be in the squad if they are transferred out
    for p1 in pids:
        for p2 in pids:
            if players[p1].position == players[p2].position and p1 != p2:
                for gw in GWS:
                    if gw > CURRENT_GW:
                        model.add(t[(p1, p2, gw)] + x[(p1, gw)] <= 1)

    # player has to have been in the squad the previous GW to be transferred out
    for gw in GWS:
        if gw > CURRENT_GW:
            for p1 in pids:
                for p2 in pids:
                    if players[p1].position == players[p2].position and p1 != p2:
                        model.add(t[(p1, p2, gw)] <= x[(p1, gw - 1)])

    # player cant be transferred in if they are already in the squad
    for gw in GWS:
        if gw > CURRENT_GW:
            for p1 in pids:
                for p2 in pids:
                    if players[p1].position == players[p2].position and p1 != p2:
                        model.add(t[(p1, p2, gw)] + x[(p2, gw - 1)] <= 1)

    # dont transfer a player out and in within the same GW, an equivalent (simpler) solution can be found
    for gw in GWS:
        if gw > CURRENT_GW:
            for p1 in pids:
                model.add(
                    cp_model.LinearExpr.sum(
                        [t[(px, p1, gw)] + t[(p1, px, gw)] for px in pids if px != p1 and players[px].position == players[p1].position]
                    )
                    <= 1
                )

    # dont transfer a player in and then out within the same GW, an equivalent (simpler) solution can be found
    for gw in GWS:
        if gw > CURRENT_GW:
            for p1 in pids:
                model.add(
                    cp_model.LinearExpr.sum(
                        [t[(p1, px, gw)] + t[(px, p1, gw)] for px in pids if px != p1 and players[px].position == players[p1].position]
                    )
                    <= 1
                )

    # <= 1 transfer per GW
    for gw in GWS:
        if gw > CURRENT_GW:
            model.add(
                cp_model.LinearExpr.sum(
                    [t[(p1, p2, gw)] for p1 in pids for p2 in pids if players[p1].position == players[p2].position and p1 != p2]
                )
                <= 1
            )

    # # don'gw play any players that are potentially injured / dont exist (cut constraint)
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
                for (p1, p2), t_val in [((p1, p2), t_val) for (p1, p2, g), t_val in t.items() if g == gw]:
                    if solver.value(t_val):
                        print(
                            f"{POS_LOOKUP[players[p1].position]}: ({players[p1].team_name}) {players[p1].name} -> ({players[p2].team_name}) {players[p2].name} (${players[p1].price / 10} -> ${players[p2].price / 10})"
                        )
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
    print(f"Maximum of objective function: {round(solver.objective_value)} ({round(solver.objective_value / len(GWS))} per GW)")
    print(f"Total Transfers: {sum([solver.value(t_val) for t_val in t.values()])}")
    print(f"status    - {solver.status_name(status)}")
    print(f"conflicts - {solver.num_conflicts}")
    print(f"branches  - {solver.num_branches}")
    print(f"wall time - {solver.wall_time} s\n")


def main():
    run_engine()


if __name__ == "__main__":
    main()
