from ortools.init.python import init
from ortools.sat.python import cp_model
import pandas as pd
import numpy as np

SEASON = "2025-26"

GK = 1
DEF = 2
MID = 3
ATT = 4

NUM_TEAMS = 20

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

    # Fetch data from CSVs for solve
    data = fetch_data()

    x = {pid: model.new_int_var(0, 1, f"x_{pid}") for pid in data["I"]}
    y = {pid: model.new_int_var(0, 1, f"y_{pid}") for pid in data["I"]}

    var = {"x": x, "y": y}

    model = build_constraints(model, var, data)

    # OBJECTIVE FUNCTION
    model.maximize(sum(x[pid] * data["XPN"][pid] for pid in data["I"]))

    solve(model, solver, data, var)


def build_constraints(model, var, data):
    x = var["x"]
    P = data["P"]
    pids = data["I"]
    positions = data["PP"]
    ptm = data["PTM"]  # player team mask

    # cost constraint
    model.add(cp_model.LinearExpr.sum([P[pid] * x[pid] for pid in pids]) <= 1000)

    # number of players in squad constraint
    model.add(cp_model.LinearExpr.sum([x[pid] for pid in pids]) == 15)

    # 2 GKs allowed
    model.add(
        cp_model.LinearExpr.sum([x[pid] * positions[pid][GK - 1] for pid in pids]) == 2
    )

    # 5 DEFs allowed
    model.add(
        cp_model.LinearExpr.sum([x[pid] * positions[pid][DEF - 1] for pid in pids]) == 5
    )

    # 5 MIDs allowed
    model.add(
        cp_model.LinearExpr.sum([x[pid] * positions[pid][MID - 1] for pid in pids]) == 5
    )

    # 3 ATTs allowed
    model.add(
        cp_model.LinearExpr.sum([x[pid] * positions[pid][ATT - 1] for pid in pids]) == 3
    )

    # max 3 players per team
    for team_code in data["TC"].keys():
        # print(team_code)
        model.add(
            cp_model.LinearExpr.sum([x[pid] * ptm[pid][team_code] for pid in pids]) <= 3
        )

    return model


def fetch_data():
    player_data = pd.read_csv(f"data/{SEASON}/players_raw.csv")
    team_data = pd.read_csv(f"data/{SEASON}/teams.csv")

    # Player Names
    N = dict(
        zip(
            player_data["id"],
            map(
                lambda n1, n2: n1 + " " + n2,
                player_data["first_name"],
                player_data["second_name"],
            ),
        )
    )

    # Prices
    P = dict(zip(player_data["id"], player_data["now_cost"]))

    # Player IDs
    I = list(player_data["id"])

    # XP Next Week
    XPN = dict(zip(player_data["id"], player_data["ep_next"]))

    # Positions
    PP = {
        player_id: [
            int(x == element_type) for x in range(1, 5)
        ]  # place a '1' in the index which corresponds to the players position
        for player_id, element_type in zip(
            player_data["id"], player_data["element_type"]
        )
    }

    # Team code -> name map
    TC = dict(zip(team_data["code"], team_data["short_name"]))

    # player -> team mask
    PTM = {
        player_id: {
            tc: int(tc == team_code) for tc in TC.keys()
        }  # place a '1' in the index which corresponds to the players position
        for player_id, team_code in zip(player_data["id"], player_data["team_code"])
    }

    # player_id -> team name map, good for printing solution
    T = {
        player_id: TC[team]
        for player_id, team in zip(player_data["id"], player_data["team_code"])
    }

    print(str(len(P)) + " players found")

    return {"P": P, "I": I, "N": N, "XPN": XPN, "PP": PP, "T": T, "TC": TC, "PTM": PTM}


def solve(model, solver, data, var):
    status = solver.solve(model)

    print(f"Status: {status}")
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        players = {}
        total_cost = 0

        # Collect results
        for [id, x_val] in var["x"].items():
            if solver.value(x_val):
                pos = data["PP"][id].index(1) + 1
                name = data["N"][id]
                cost = data["P"][id] / 10
                team = data["T"][id]
                total_cost += cost

                details = [{"id": id, "name": name, "cost": cost, "team": team}]

                if players.get(pos):
                    players[pos] += details
                else:
                    players[pos] = details

        # Display
        print(f"Maximum of objective function: {solver.objective_value}\n")

        for pos, pos_players in players.items():
            print(f"{POS_LOOKUP[pos]}")
            print("---------------------------------------")

            for p in pos_players:
                print(f"({p['team']}) {p['name']} ({p['id']}) (cost: {p['cost']})")

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
