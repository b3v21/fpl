from ortools.init.python import init
from ortools.sat.python import cp_model
from dataloader import Dataloader

SEASON = "2025-26"

GK = 1
DEF = 2
MID = 3
ATT = 4

POS_LOOKUP = {GK: "Goalkeepers", DEF: "Defenders", MID: "Midfielders", ATT: "Attackers"}


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

    x = {pid: model.new_int_var(0, 1, f"x_{pid}") for pid in DL.player_ids}
    y = {pid: model.new_int_var(0, 1, f"y_{pid}") for pid in DL.player_ids}

    var = {"x": x, "y": y}

    model = build_constraints(model, var)

    # OBJECTIVE FUNCTION
    model.maximize(
        sum(y[pid] * DL.player_expected_points[pid] for pid in DL.player_ids)
        + sum(y[pid] * (3 - DL.player_fixture_difficulty[pid]) for pid in DL.player_ids)
    )
    # in this niave model, a fixture difficultly of '1' gives the player an XP of +2, '2' is +1, '3' is 0, '4' is -1 and '5' is -2,
    # this is done via the linear function 3 - DF

    solve(model, solver, var)


def build_constraints(model, var):
    x, y = var["x"], var["y"]

    # Fetch data from dataloader singleton
    DL = Dataloader()

    pids = DL.player_ids

    # cost constraint
    model.add(cp_model.LinearExpr.sum([DL.player_price[pid] * x[pid] for pid in pids]) <= 1000)

    # we generally want to have most of our money in the team (TODO: this constraint MIGHT be removed later)
    model.add(cp_model.LinearExpr.sum([DL.player_price[pid] * x[pid] for pid in pids]) >= 970)

    # number of players in squad constraint
    model.add(cp_model.LinearExpr.sum([x[pid] for pid in pids]) == 15)

    # 2 GKs allowed
    model.add(cp_model.LinearExpr.sum([x[pid] * DL.player_position_mask[pid][GK - 1] for pid in pids]) == 2)

    # 5 DEFs allowed
    model.add(cp_model.LinearExpr.sum([x[pid] * DL.player_position_mask[pid][DEF - 1] for pid in pids]) == 5)

    # 5 MIDs allowed
    model.add(cp_model.LinearExpr.sum([x[pid] * DL.player_position_mask[pid][MID - 1] for pid in pids]) == 5)

    # 3 ATTs allowed
    model.add(cp_model.LinearExpr.sum([x[pid] * DL.player_position_mask[pid][ATT - 1] for pid in pids]) == 3)

    # 1 GK on the field
    model.add(cp_model.LinearExpr.sum([y[pid] * DL.player_position_mask[pid][GK - 1] for pid in pids]) == 1)

    # 3-5 DEFs on the field
    model.add(cp_model.LinearExpr.sum([y[pid] * DL.player_position_mask[pid][DEF - 1] for pid in pids]) >= 3)
    model.add(cp_model.LinearExpr.sum([y[pid] * DL.player_position_mask[pid][DEF - 1] for pid in pids]) <= 5)

    # 2-5 MIDs on the field
    model.add(cp_model.LinearExpr.sum([y[pid] * DL.player_position_mask[pid][MID - 1] for pid in pids]) >= 2)
    model.add(cp_model.LinearExpr.sum([y[pid] * DL.player_position_mask[pid][MID - 1] for pid in pids]) <= 5)

    # 1-3 ATTs on the field
    model.add(cp_model.LinearExpr.sum([y[pid] * DL.player_position_mask[pid][ATT - 1] for pid in pids]) >= 1)
    model.add(cp_model.LinearExpr.sum([y[pid] * DL.player_position_mask[pid][ATT - 1] for pid in pids]) <= 3)

    # max 3 players per team
    for team_code in DL.team_code_name.keys():
        model.add(cp_model.LinearExpr.sum([x[pid] * DL.player_team_mask[pid][team_code] for pid in pids]) <= 3)

    # max 11 players on the field
    model.add(cp_model.LinearExpr.sum([y[pid] for pid in pids]) == 11)

    # a player must be in the team in order to be on the field
    for pid in pids:
        model.add(y[pid] <= x[pid])

    # don't play any players that are potentially injured / dont exist (cut constraint)
    for pid in pids:
        if DL.player_chance_of_playing[pid] < 75:
            model.add(y[pid] == 0)

    return model


def solve(model, solver, var):
    status = solver.solve(model)

    # Fetch data from dataloader singleton
    DL = Dataloader()

    # unpack vars
    x, y = var["x"], var["y"]

    print(f"Status: {status}")
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        players = {}
        total_cost = 0

        # Collect results
        for [id, x_val] in x.items():
            if solver.value(x_val):
                pos = DL.player_position_mask[id].index(1) + 1
                name = DL.player_name[id]
                cost = DL.player_price[id] / 10
                team = DL.player_team_name[id]
                total_cost += cost

                details = [
                    {
                        "id": id,
                        "name": name,
                        "cost": cost,
                        "team": team,
                        "playing": solver.value(y[id]),
                    }
                ]

                if players.get(pos):
                    players[pos] += details
                else:
                    players[pos] = details

        # Display
        print(f"Maximum of objective function: {round(solver.objective_value)}\n")

        for pos, pos_players in players.items():
            print(f"{POS_LOOKUP[pos]}")
            print("---------------------------------------")

            for p in pos_players:
                playing = " - PLAYING" if p["playing"] else ""
                print(f"({p['team']}) {p['name']} ({p['id']}) (cost: {p['cost']})" + playing)

            print("")

        print("\nTotal Cost: " + str(round(total_cost, 1)))

    else:
        print("No solution found.")

    # Statistics.
    print("\nStatistics")
    print(f"  status   : {solver.status_name(status)}")
    print(f"  conflicts: {solver.num_conflicts}")
    print(f"  branches : {solver.num_branches}")
    print(f"  wall time: {solver.wall_time} s")


def main():
    run_engine()


if __name__ == "__main__":
    main()
