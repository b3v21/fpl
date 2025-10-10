from constants import CURRENT_GW, DASH, POS_LOOKUP, FUTURE_GWS, FUTURE_GWS_WITHOUT_CURR
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
            self.solver = solver
            self.vars = var

            self.build_solution()

    def build_solution(self):
        x, y, t, wc, wc_used, fh, fh_used, tc, tc_used, bb_used, c, b, bench_boost_points = self.vars

        self.team: dict[int, list[Player]] = {}
        self.wildcards: list[int] = []
        self.free_hits: list[int] = []
        self.triple_captains: list[int] = []
        self.bench_boosts: list[int] = []

        self.transfers_in: dict[int, list[Player]] = {}
        self.transfers_out: dict[int, list[Player]] = {}
        self.free_hit_transfers: dict[int, list[Player]] = {}
        self.wildcard_transfers: dict[int, list[Player]] = {}
        self.triple_captained_player: dict[int, Player] = {}

        # Collect results
        for [(id, gw), x_val] in x.items():
            if self.solver.value(x_val):
                player = self.players[id]
                if self.team.get((gw, player.position)):
                    self.team[(gw, player.position)] += [player]
                else:
                    self.team[(gw, player.position)] = [player]

        # Collect WC Usage
        for [gw, val] in wc.items():
            if self.solver.value(val):
                self.wildcards.append(gw)

        # Collect FH Usage
        for [gw, val] in fh.items():
            if self.solver.value(val):
                self.free_hits.append(gw)

        # Collect TC Usage
        for [(id, gw), val] in tc.items():
            if self.solver.value(val):
                self.triple_captains.append(gw)
                self.triple_captained_player[gw] = self.players[id]

        # Collect BB Usage
        for [gw, val] in bb_used.items():
            if self.solver.value(val):
                self.bench_boosts.append(gw)

        # Collect incoming Transfers
        for gw in FUTURE_GWS_WITHOUT_CURR:
            for pid in [p for (p, g), val in x.items() if g == gw and (self.solver.value(val) - self.solver.value(x[(p, g - 1)])) == 1]:
                if gw in self.free_hits:
                    self.free_hit_transfers[gw] = self.free_hit_transfers.get(gw, []) + [self.players[pid]]
                elif gw in self.wildcards:
                    self.wildcard_transfers[gw] = self.wildcard_transfers.get(gw, []) + [self.players[pid]]
                else:
                    self.transfers_in[gw] = self.transfers_in.get(gw, []) + [self.players[pid]]

        # Collect outgoing Transfers
        for gw in FUTURE_GWS_WITHOUT_CURR:
            for pid in [p for (p, g), val in x.items() if g == gw and (self.solver.value(x[(p, g - 1)]) - self.solver.value(val)) == 1]:
                self.transfers_out[gw] = self.transfers_out.get(gw, []) + [self.players[pid]]

        return

    def was_chip_used(self, gw):
        chip = ""

        if gw in self.wildcards:
            chip = colored(" - WILD CARD", "yellow")
        elif gw in self.free_hits:
            chip = colored(" - FREE HIT", "yellow")
        elif gw in self.bench_boosts:
            chip = colored(" - BENCH BOOST", "yellow")
        elif gw in self.triple_captains:
            chip = colored(f" - TRIPLE CAPTAIN ({self.triple_captained_player[gw].name})", "yellow")

        return chip

    def __str__(self):
        x, y, t, wc, wc_used, fh, fh_used, tc, tc_used, bb_used, c, b, bench_boost_points = self.vars

        str_res = ""
        total_exp = 0

        for gw in reversed(FUTURE_GWS):
            exp_points = 0

            str_res += LINE
            str_res += f"GAMEWEEK {gw}"

            str_res += self.was_chip_used(gw)
            str_res += NEW_LINE
            str_res += LINE

            # TRANSFERS IN
            if gw in self.transfers_in.keys():
                for p in self.transfers_in[gw]:
                    vs = self.DL.teams[self.DL.team_vs_team[(p.team.id, gw)]]
                    str_res += colored(f"({POS_LOOKUP[p.position]}) {p.name} (£{p.price / 10})", "green") + f" vs ({vs})\n"

            elif gw in self.wildcard_transfers.keys():
                for p in self.wildcard_transfers[gw]:
                    vs = self.DL.teams[self.DL.team_vs_team[(p.team.id, gw)]]
                    str_res += colored(f"({POS_LOOKUP[p.position]}) {p.name} (£{p.price / 10})", "yellow") + f" vs ({vs})\n"

            elif gw in self.free_hit_transfers.keys():
                for p in self.free_hit_transfers[gw]:
                    vs = self.DL.teams[self.DL.team_vs_team[(p.team.id, gw)]]
                    str_res += colored(f"({POS_LOOKUP[p.position]}) {p.name} (£{p.price / 10})", "yellow") + f" vs ({vs})\n"

            # TRANSFERS OUT
            if gw in self.transfers_out.keys():
                for p in self.transfers_out[gw]:
                    vs = self.DL.teams[self.DL.team_vs_team[(p.team.id, gw)]]
                    str_res += colored(f"({POS_LOOKUP[p.position]}) {p.name} (£{p.price / 10})", "red") + f" WAS vs ({vs})\n"
                str_res += LINE

            for pos, pos_name in POS_LOOKUP.items():
                str_res += f"{pos_name}:\n"
                for player in self.team[(gw, pos)]:
                    vs = self.DL.teams[self.DL.team_vs_team[(player.team.id, gw)]]
                    str_res += f"({player.team}) {player.name} (price: {player.price / 10})"

                    if self.solver.value(y[(player.id, gw)]):
                        exp_points += self.DL.player_future_xp[(player.id, gw)]
                        str_res += colored(" PLAYING", "light_green") + f" vs ({vs})"
                    else:
                        if gw in self.bench_boosts:
                            exp_points += self.DL.player_future_xp[(player.id, gw)]
                        str_res += colored(" BENCH", "light_red") + f" vs ({vs})"

                    if self.solver.value(tc[(player.id, gw)]):
                        str_res += colored(" (c)", "yellow")
                    elif self.solver.value(c[(player.id, gw)]):
                        str_res += colored(" (c)", "blue")

                    str_res += NEW_LINE

                str_res += NEW_LINE

            str_res += f"Gameweek Expected Points: {round(exp_points)}"
            total_exp += round(exp_points)
            str_res += NEW_LINE

            str_res += LINE
            str_res += NEW_LINE

        str_res += DASH * 35 + " SUMMARY " + DASH * 36 + NEW_LINE
        str_res += colored(f"Total Expected Points: {round(total_exp)} ({round(total_exp/len(FUTURE_GWS))} on average)", "green") + NEW_LINE
        str_res += NEW_LINE
        for gw in FUTURE_GWS:
            if gw > CURRENT_GW:
                if gw in self.free_hits:
                    transfers = f"{len(self.free_hit_transfers[gw])} transfer(s)"
                elif gw in self.wildcards:
                    transfers = f"{len(self.wildcard_transfers[gw])} transfer(s)"
                elif gw in self.transfers_in.keys():
                    transfers = f"{len(self.transfers_in[gw])} transfer(s)"
                else:
                    transfers = "ROLLED"
            else:
                transfers = "N/A"
            chip = self.was_chip_used(gw)
            str_res += f"GAMEWEEK {gw}: {transfers}{chip}"
            str_res += NEW_LINE
        str_res += LINE

        return str_res
