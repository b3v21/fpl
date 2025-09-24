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

    x = {(pid, t): model.new_int_var(0, 1, f"x_{pid}") for pid in DL.player_ids for t in GWS}
    y = {(pid, t): model.new_int_var(0, 1, f"y_{pid}") for pid in DL.player_ids for t in GWS}

    var = [x, y]

    model = build_constraints(model, var)

    # OBJECTIVE FUNCTION
    model.maximize(
        sum(y[(pid, t)] * DL.player_expected_points[(pid, t)] for pid in DL.player_ids for t in GWS)
        + sum(y[(pid, t)] * (3 - DL.player_fixture_difficulty[(pid, t)]) for pid in DL.player_ids for t in GWS)
    )
    # in this niave model, a fixture difficultly of '1' gives the player an XP of +2, '2' is +1, '3' is 0, '4' is -1 and '5' is -2,
    # this is done via the linear function 3 - DF

    solve(model, solver, var)


def build_constraints(model, var):
    x, y = var

    # Fetch data from dataloader singleton
    DL = Dataloader()

    pids = DL.player_ids

    # cost constraint
    for t in GWS:
        model.add(
            cp_model.LinearExpr.sum([DL.player_price[pid] * x[(pid, t)] for pid in pids]) <= 1000
        )  # TODO: somehow project player price and add it to the data?

    # we generally want to have most of our money in the team (TODO: this constraint MIGHT be removed later)
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([DL.player_price[pid] * x[(pid, t)] for pid in pids]) >= 970)

    # number of players in squad constraint
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, t)] for pid in pids]) == 15)

    # 2 GKs allowed
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, t)] * DL.player_position_mask[pid][GK - 1] for pid in pids]) == 2)

    # 5 DEFs allowed
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, t)] * DL.player_position_mask[pid][DEF - 1] for pid in pids]) == 5)

    # 5 MIDs allowed
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, t)] * DL.player_position_mask[pid][MID - 1] for pid in pids]) == 5)

    # 3 ATTs allowed
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([x[(pid, t)] * DL.player_position_mask[pid][ATT - 1] for pid in pids]) == 3)

    # 1 GK on the field
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] * DL.player_position_mask[pid][GK - 1] for pid in pids]) == 1)

    # 3-5 DEFs on the field
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] * DL.player_position_mask[pid][DEF - 1] for pid in pids]) >= 3)
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] * DL.player_position_mask[pid][DEF - 1] for pid in pids]) <= 5)

    # 2-5 MIDs on the field
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] * DL.player_position_mask[pid][MID - 1] for pid in pids]) >= 2)
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] * DL.player_position_mask[pid][MID - 1] for pid in pids]) <= 5)

    # 1-3 ATTs on the field
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] * DL.player_position_mask[pid][ATT - 1] for pid in pids]) >= 1)
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] * DL.player_position_mask[pid][ATT - 1] for pid in pids]) <= 3)

    # max 3 players per team
    for t in GWS:
        for team_code in DL.team_code_name.keys():
            model.add(cp_model.LinearExpr.sum([x[(pid, t)] * DL.player_team_mask[pid][team_code] for pid in pids]) <= 3)

    # max 11 players on the field
    for t in GWS:
        model.add(cp_model.LinearExpr.sum([y[(pid, t)] for pid in pids]) == 11)

    # a player must be in the team in order to be on the field
    for pid in pids:
        for t in GWS:
            model.add(y[(pid, t)] <= x[(pid, t)])

    # don't play any players that are potentially injured / dont exist (cut constraint)
    for pid in pids:
        for t in GWS:
            if DL.player_chance_of_playing[pid] < 75:
                model.add(y[(pid, t)] == 0)

    return model


def solve(model, solver, var):
    status = solver.solve(model)

    # Fetch data from dataloader singleton
    DL = Dataloader()

    # unpack vars
    x, y = var

    print(f"Status: {status}")
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        results = {}
        total_cost = 0

        # Collect results
        for [(id, t), x_val] in x.items():
            if solver.value(x_val):
                pos = DL.player_position_mask[id].index(1) + 1
                name = DL.player_name[id]
                cost = DL.player_price[id] / 10
                team = DL.player_team_name[id]
                total_cost += cost

                # TODO: need to make a player class to greatly simplify storing this information
                details = {"id": id, "name": name, "cost": cost, "team": team, "playing": solver.value(y[(id, t)])}

                if results.get((t, pos)):
                    results[(t, pos)] += [details]
                else:
                    results[(t, pos)] = [details]

        # Display
        for t in reversed(GWS):
            print(f"GAMEWEEK {t}")
            print("------------------------------------------------------")
            for pos_value, pos_name in POS_LOOKUP.items(): # for each position, find all players for this GW
                print(f"{pos_name}:")
                for (t, pos), players in [(key,players) for (key,players) in results.items() if pos_value in key and t in key]:
                    for p in players:
                        playing = " - PLAYING" if p["playing"] else ""
                        print(f"({p['team']}) {p['name']} ({p['id']}) (cost: {p['cost']})" + playing)

                print("")

        print("\nTotal Cost: " + str(round(total_cost, 1)))

    else:
        print("No solution found.")

    # Statistics.
    print("\nStatistics")
    print(f"Maximum of objective function: {round(solver.objective_value)}\n")
    print(f"  status   : {solver.status_name(status)}")
    print(f"  conflicts: {solver.num_conflicts}")
    print(f"  branches : {solver.num_branches}")
    print(f"  wall time: {solver.wall_time} s")


def main():
    run_engine()


if __name__ == "__main__":
    main()
