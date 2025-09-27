from ortools.init.python import init
from ortools.sat.python import cp_model
from dataloader import Dataloader, GWS

GK = 1
DEF = 2
MID = 3
ATT = 4

POS_LOOKUP = {GK: "GK", DEF: "DEF", MID: "MID", ATT: "ATT"}


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

    x = {(pid, t): model.new_int_var(0, 1, f"x_{pid}") for pid in pids for t in GWS}
    y = {(pid, t): model.new_int_var(0, 1, f"y_{pid}") for pid in pids for t in GWS}

    var = [x, y]

    model = build_constraints(model, var)

    # OBJECTIVE FUNCTION
    model.maximize(
        sum(y[(pid, t)] * players[pid].xp[t] for pid in pids for t in GWS)
        + sum(y[(pid, t)] * (3 - players[pid].vs_team_diff[t]) for pid in pids for t in GWS)
    )
    # in this niave model, a fixture difficultly of '1' gives the player an XP of +2, '2' is +1, '3' is 0, '4' is -1 and '5' is -2,
    # this is done via the linear function 3 - DF

    solve(model, solver, var)


def build_constraints(model, var):
    x, y = var

    # Fetch data from dataloader singleton
    DL = Dataloader()
    players = DL.players
    pids = players.keys()

    # cost constraint
    for t in GWS:
        model.add(
            cp_model.LinearExpr.sum([players[pid].price * x[(pid, t)] for pid in pids]) <= 1000
        )  # TODO: somehow project player price and add it to the data?

    # we generally want to have most of our money in the team (TODO: this constraint MIGHT be removed later)
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([players[pid].price * x[(pid, t)] for pid in pids]) >= 970)

    # number of players in squad constraint
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, t)] for pid in pids]) == 15)

    # 2 GKs allowed
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, t)] for pid in pids if players[pid].position == GK]) == 2)

    # 5 DEFs allowed
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, t)] for pid in pids if players[pid].position == DEF]) == 5)

    # 5 MIDs allowed
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, t)] for pid in pids if players[pid].position == MID]) == 5)

    # 3 ATTs allowed
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, t)] for pid in pids if players[pid].position == ATT]) == 3)

    # 1 GK on the field
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] for pid in pids if players[pid].position == GK]) == 1)

    # 3-5 DEFs on the field
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] for pid in pids if players[pid].position == DEF]) >= 3)
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] for pid in pids if players[pid].position == DEF]) <= 5)

    # 2-5 MIDs on the field
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] for pid in pids if players[pid].position == MID]) >= 2)
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] for pid in pids if players[pid].position == MID]) <= 5)

    # 1-3 ATTs on the field
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] for pid in pids if players[pid].position == ATT]) >= 1)
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] for pid in pids if players[pid].position == ATT]) <= 3)

    # # max 3 players per team
    for t in GWS:
        for team_code in DL.team_code_name.keys():
            model.add(cp_model.LinearExpr.sum([x[(pid, t)] for pid in pids if players[pid].team_code == team_code]) <= 3)

    # max 11 players on the field
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] for pid in pids]) == 11)

    # a player must be in the team in order to be on the field
    for pid in pids:
        for t in GWS:
            model.add(y[(pid, t)] <= x[(pid, t)])

    # # don't play any players that are potentially injured / dont exist (cut constraint)
    # for pid in pids:
    #     for t in GWS:
    #         if DL.player_chance_of_playing[pid] < 75:
    #             model.add(y[(pid, t)] == 0)

    return model


def solve(model, solver, var):
    status = solver.solve(model)

    # Fetch data from dataloader singleton
    DL = Dataloader()
    players = DL.players

    # unpack vars
    x, y = var

    print(f"Status: {status}")
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        results: list[Player] = {}

        # Collect results
        for [(id, t), x_val] in x.items():
            if solver.value(x_val):
                if results.get(t):
                    results[t] += [players[id]]
                else:
                    results[t] = [players[id]]

        # Display
        for t in reversed(GWS):
            total_cost = 0
            print(f"GAMEWEEK {t}")
            print("------------------------------------------------------")
            for pos_value, pos_name in POS_LOOKUP.items():  # for each position, find all players for this GW
                print(f"{pos_name}:")
                for p in [r for r in results[t] if r.position == pos_value]:
                    total_cost += p.price / 10
                    playing = " - PLAYING" if solver.value(y[(p.id, t)]) else ""
                    vs = DL.team_code_name[DL.team_id_team_code[p._vs_team_id[t]]]

                    print(f"({p.team_name}) {p.name} ({p.id}) (price: {p.price / 10}) vs ({vs})", playing)

                print("")

            print("Team Value: " + str(round(total_cost, 1)))
            print("Money in Bank: " + str(round(100 - total_cost, 1)))
            print("")

        print("------------------------------------------------------")

    else:
        print("No solution found.")

    print("\nStatistics:")
    print(f"Maximum of objective function: {round(solver.objective_value)} ({round(solver.objective_value / len(GWS))} per GW)")
    print(f"status    - {solver.status_name(status)}")
    print(f"conflicts - {solver.num_conflicts}")
    print(f"branches  - {solver.num_branches}")
    print(f"wall time - {solver.wall_time} s\n")


def main():
    run_engine()


if __name__ == "__main__":
    main()
