import argparse
import pandas as pd
import random
from tabulate import tabulate

from cards import card_int, suit_int, SUITS
from game import EuchreGame
from strategy import *

"""
simulation.py — Monte Carlo hand simulations for Euchre EV
"""


class SimulationStats:
    def __init__(self):
        self.trials = 0
        self.tricks = 0
        self.points = 0
        self.wins = 0
        self.point_counts = {score: 0 for score in (-4, -2, -1, 1, 2, 4)}

    def record(self, outcome: dict):
        points = outcome["points"]
        self.trials += 1
        self.tricks += outcome["tricks"]
        self.points += points
        if outcome["is_win"]:
            self.wins += 1
        self.point_counts[points] += 1

    def report(self):
        trials = self.trials or 1  # Avoid errors if 0 trials
        return {
            "trials": self.trials,
            "avg_tricks": self.tricks / self.trials if self.trials else 0,
            "avg_points": self.points / self.trials if self.trials else 0,
            "win_rate": self.wins / self.trials if self.trials else 0,
            # Point outcome probabilities
            "p_-4": self.point_counts[-4] / trials,
            "p_-2": self.point_counts[-2] / trials,
            "p_-1": self.point_counts[-1] / trials,
            "p_1": self.point_counts[1] / trials,
            "p_2": self.point_counts[2] / trials,
            "p_4": self.point_counts[4] / trials,
        }


def simulate_hand(
    fixed_hand: list[int],
    fixed_upcard: int,
    fixed_seat: int,
    trials: int,
    force_suit_choice: int = None,
    force_alone_choice: bool = False,
    strategies: list[Strategy] = None,
    rng_seed: int = None,
    verbose: bool = False,
):
    """
    fixed_seat of 0 is dealer
    """
    stats = SimulationStats()
    rng = random.Random(rng_seed)

    if strategies is None:
        strategies = [SimpleStrategy() for _ in range(4)]

    for i in range(trials):
        game = EuchreGame(strategies=strategies, verbose=verbose)

        outcome = game.play_hand(
            True,
            fixed_hand,
            fixed_upcard,
            fixed_seat,
            force_suit_choice,
            force_alone_choice,
            rng,
        )
        stats.record(outcome)

    return stats.report()


# Example CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=50000)
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    hand = ["Jc", "Js", "Jh", "Jd", "9d"]
    upcard = "9h"
    # hand = ["9c", "Tc", "Jc", "Qc", "Kc"]
    # upcard = "Ac"
    seat = 0
    # seat = 1
    # seat = 2
    # seat = 3

    # my_strat = PassiveStrategy()
    my_strat = SimpleStrategy()
    # others_strats = [PassiveStrategy() for _ in range(3)]
    others_strats = [SimpleStrategy() for _ in range(3)]

    hand_int = card_int(hand)
    upcard_int = card_int(upcard)

    strategies = others_strats.copy()
    strategies.insert(seat, my_strat)

    # print("Simulate passing always")
    """
    force_suit_name = None
    # force_suit_name = "clubs"
    # force_suit_name = "diamonds"
    # force_suit_name = "hearts"
    # force_suit_name = "spades"
    # force_suit_name = "pass"
    force_alone_choice = None
    # force_alone_choice = False
    # force_alone_choice = True
    force_suit_choice = suit_int(force_suit_name)
    report_pass = simulate_hand(
        hand_int,
        upcard_int,
        seat,
        args.trials,
        force_suit_choice,
        force_alone_choice,
        strategies,
        args.seed,
        args.verbose,
    )
    print(report_pass)
    exit()
    """

    force_suit_names = ["clubs", "diamonds", "hearts", "spades", "pass"]
    # force_suit_names = ["diamonds"]
    force_alone_choices = [False, True]
    force_suit_choices = suit_int(force_suit_names)

    # Collect results for all combinations
    results = []
    for force_suit_choice in force_suit_choices:
        for force_alone_choice in force_alone_choices:
            # Dealer can't always pass, so no reason to simulate this
            if seat == 0 and force_suit_choice == -1:
                continue
            result = simulate_hand(
                hand_int,
                upcard_int,
                seat,
                args.trials,
                force_suit_choice,
                force_alone_choice,
                strategies,
                args.seed,
                args.verbose,
            )
            result = {
                "Suit to Call": (
                    SUITS[force_suit_choice] if force_suit_choice != -1 else "Pass"
                ),
                "Alone": force_alone_choice,
            } | result
            results.append(result)

    # Print results as a table
    # print(tabulate(results, headers="keys", tablefmt="grid"))
    print(pd.DataFrame(results))
