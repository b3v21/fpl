from constants import GWS, CURRENT_GW, DASH, POS_LOOKUP
from player import Player
from termcolor import colored
from ortools.sat.python import cp_model
from dataloader import Dataloader

LINE = DASH * 80 + "\n"
NEW_LINE = "\n"


class Solution:
    def __init__(self, var, status, solver):
        print(f"Status: {status}")
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # Fetch data from dataloader singleton
            self.DL = Dataloader()
            self.players = self.DL.players

            self.build_solution(var, solver)
        else:
            print("\nNo Solution Found")

    def build_solution(self, var, solver):
        x, y, t, wc, wc_used, fh, fh_used, tc, tc_used, bb_used, c, b, bench_boost_points = var

        self.team: list[Player] = {}
        self.wildcards = []
        self.free_hits = []
        self.triple_captains = []
        self.bench_boosts = []

        self.transfers_in = {}
        self.transfers_out = {}
        self.free_hit_transfers = {}
        self.wildcard_transfers = {}
        self.triple_captained_player = {}

        # Collect results
        for [(id, gw), x_val] in x.items():
            if solver.value(x_val):
                if self.team.get(gw):
                    self.team[gw] += [self.players[id]]
                else:
                    self.team[gw] = [self.players[id]]

        # Collect WC Usage
        for [gw, val] in wc.items():
            if solver.value(val):
                self.wildcards.append(gw)

        # Collect FH Usage
        for [gw, val] in fh.items():
            if solver.value(val):
                self.free_hits.append(gw)

        # Collect TC Usage
        for [(id, gw), val] in tc.items():
            if solver.value(val):
                self.triple_captains.append(gw)
                self.triple_captained_player[gw] = self.players[id]

        # Collect BB Usage
        for [gw, val] in bb_used.items():
            if solver.value(val):
                self.bench_boosts.append(gw)

        # Collect incoming Transfers
        for gw in GWS:
            if gw > CURRENT_GW:
                for pid in [p for (p, g), val in x.items() if g == gw and (solver.value(val) - solver.value(x[(p, g - 1)])) == 1]:
                    if gw in self.free_hits:
                        self.free_hit_transfers[gw] = self.free_hit_transfers.get(gw, []) + [self.players[pid]]
                    elif gw in self.wildcards:
                        self.wildcard_transfers[gw] = self.wildcard_transfers.get(gw, []) + [self.players[pid]]
                    else:
                        self.transfers_in[gw] = self.transfers_in.get(gw, []) + [self.players[pid]]

        # Collect outgoing Transfers
        for gw in GWS:
            if gw > CURRENT_GW:
                for pid in [p for (p, g), val in x.items() if g == gw and (solver.value(x[(p, g - 1)]) - solver.value(val)) == 1]:
                    if gw - 1 not in self.free_hits:
                        self.transfers_out[gw] = self.transfers_out.get(gw, []) + [self.players[pid]]

        return

    def __str__(self):
        str_res = ""

        for gw in reversed(GWS):
            str_res += LINE
            str_res += f"GAMEWEEK {gw}"
            chip = "\n"

            if gw in self.wildcards:
                chip = colored(" - WILD CARD\n", "yellow")
            elif gw in self.free_hits:
                chip = colored(" - FREE HIT\n", "yellow")
            elif gw in self.bench_boosts:
                chip = colored(" - BENCH BOOST\n", "yellow")
            elif gw in self.triple_captains:
                chip = colored(f" - TRIPLE CAPTAIN ({self.triple_captained_player[gw].name})\n", "yellow")

            str_res += chip
            str_res += LINE

            # TRANSFERS IN
            if gw in self.transfers_in.keys():
                str_res += colored("IN:\n", "green")
                for p in self.transfers_in[gw]:
                    str_res += f"({POS_LOOKUP[p.position]}) {p.name} (£{p.price / 10})\n"
                    
            elif gw in self.wildcard_transfers.keys():
                str_res += colored("IN (WILD CARD):\n", "green")
                for p in self.wildcard_transfers[gw]:
                    str_res += f"({POS_LOOKUP[p.position]}) {p.name} (£{p.price / 10})\n"
                    
            elif gw in self.free_hit_transfers.keys():
                str_res += colored("IN (FREE HIT):\n", "green")
                for p in self.free_hit_transfers[gw]:
                    str_res += f"({POS_LOOKUP[p.position]}) {p.name} (£{p.price / 10})\n"

            # TRANSFERS OUT
            if gw in self.transfers_out.keys():
                str_res += colored("\nOUT:\n", "red")
                for p in self.transfers_out[gw]:
                    str_res += f"({POS_LOOKUP[p.position]}) {p.name} (£{p.price / 10})\n"
                str_res += LINE
                
            for player in self.team[gw]:
                vs = self.DL.team_code_name[self.DL.team_id_team_code[player._vs_team_id[gw]]]
                str_res += f"({player.team_name}) {player.name} ({player.id}) (price: {player.price / 10}) vs ({vs})\n"
                
            str_res += LINE
            str_res += NEW_LINE

        return str_res

        #     # Display
        #     for gw in reversed(GWS):
        #         total_cost = 0
        #         print(DASH * 80)
        #         if gw == CURRENT_GW:
        #             print(f"GAMEWEEK {gw}")
        #         if gw > CURRENT_GW:
        #             print(f"GAMEWEEK {gw}" + solver.value(fh_used[gw]) * " - FREE HIT USED" + solver.value(wc_used[gw]) * " - WILD CARD USED")
        #             print(DASH * 80)
        #             print("Transfers:")
        #             for p1 in [p for (p, g), val in x.items() if g == gw and (solver.value(val) - solver.value(x[(p, g - 1)])) == 1]:
        #                 print("IN:", f"({POS_LOOKUP[players[p1].position]})", players[p1].name, f"(£{players[p1].price / 10})")
        #                 if not solver.value(fh_used[gw]) and not solver.value(wc_used[gw]):
        #                     transfer_count[gw] = transfer_count.get(gw, 0) + 1
        #             print("")
        #             for p2 in [p for (p, g), val in x.items() if g == gw and (solver.value(x[(p, g - 1)]) - solver.value(val)) == 1]:
        #                 print("OUT:", f"({POS_LOOKUP[players[p2].position]})", players[p2].name, f"(£{players[p2].price / 10})")
        #         print(DASH * 80)
        #         for pos_value, pos_name in POS_LOOKUP.items():  # for each position, find all players for this GW
        #             print(f"{pos_name}:")
        #             for p in [r for r in team[gw] if r.position == pos_value]:
        #                 total_cost += p.price / 10
        #                 playing = colored("PLAYING", "green") if solver.value(y[(p.id, gw)]) else ""
        #                 captain = colored(" (CAPTAIN)", "light_yellow") if solver.value(c[(p.id, gw)]) else ""
        #                 bench = colored("BENCH", "red") if solver.value(b[(p.id, gw)]) else ""
        #                 vs = DL.team_code_name[DL.team_id_team_code[p._vs_team_id[gw]]]

        #                 print(f"({p.team_name}) {p.name} ({p.id}) (price: {p.price / 10}) vs ({vs}) - " + playing + bench + captain)

        #             print("")

        #         print("Team Value: " + str(round(total_cost, 1)))
        #         print("Money in Bank: " + str(round(100 - total_cost, 1)))
        #         print("")

        #     print(DASH * 80)

        # else:
        #     print("No solution found.")

        # print(f"Maximum of objective function: {round(solver.objective_value)} ({round(solver.objective_value / len(GWS))} per GW)")

        # print(f"Total Transfers: {sum(transfer_count.values())}")

        # # ({len(GWS) - 1 - sum(transfer_count.values()) - len(free_hits.keys()) - len(wildcards.keys())} left over)"

        # print(f"\nTransfers per GW:")
        # for gw in GWS:
        #     if gw > CURRENT_GW:
        #         if gw in wildcards.keys():
        #             print(f"GW {gw}: WILDCARD USED ({wildcards[gw]} transfers)")
        #         elif gw in free_hits.keys():
        #             print(f"GW {gw}: FREE HIT USED ({free_hits[gw]} transfers)")
        #         else:
        #             print(f"GW {gw}: {transfer_count.get(gw, 'ROLL')}")

        # print("")
        # print("Wild Card used in: ")
        # for gw, transfers in wildcards.items():
        #     print(f"GAMEWEEK {gw} ({transfers} transfers)")
        # print("")
        # print("Free Hit used in: ")
        # for gw, t in free_hits.items():
        #     print(f"GAMEWEEK {gw} ({t} transfers)")
        # print("")
        # print("Triple Captain used in: ")
        # for gw, player in triple_captains.items():
        #     print(f"GAMEWEEK {gw} ({player.name})")
        # print("")
        # print("Bench Boost used in: ")
        # for gw in bench_boost.keys():
        #     print(f"GAMEWEEK {gw}")
