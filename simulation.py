import argparse
import pandas as pd
import random
from tabulate import tabulate
from typing import Any

from cards import card_int, CARD_NAME, suit_int, SUITS
from game import EuchreGame
from strategy import *

"""
simulation.py — Monte Carlo hand simulations for Euchre EV
"""


class SimulationStats:
    def __init__(self, split_by_maker: bool = False):
        # Optional to track separately by whether or not we actually called trump
        self.split_by_maker = split_by_maker
        if split_by_maker:
            self.by_maker = {
                True: SimulationStats(split_by_maker=False),
                False: SimulationStats(split_by_maker=False),
            }
            return

        self.trials = 0
        self.tricks = 0
        self.points = 0
        self.wins = 0
        self.point_counts = {score: 0 for score in (-4, -2, -1, 1, 2, 4)}

    def record(self, outcome: dict):
        if self.split_by_maker:
            self.by_maker[outcome["is_maker"]].record(outcome)
            return

        points = outcome["points"]
        self.trials += 1
        self.tricks += outcome["tricks"]
        self.points += points
        if outcome["is_win"]:
            self.wins += 1
        self.point_counts[points] += 1

    def report(self):
        if self.split_by_maker:
            rows = []
            for maker, stats in self.by_maker.items():
                base = stats.report()
                rows.append({"Maker": maker, **base})
            return rows

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


def position_from_seat(seat: int) -> int:
    if seat not in (0, 1, 2, 3):
        raise ValueError(f"Invalid seat: {seat}")

    return 4 if seat == 0 else seat


def position_str_from_seat(seat: int) -> str:
    if seat not in (0, 1, 2, 3):
        raise ValueError(f"Invalid seat: {seat}")

    position_map = {0: "Dealer", 1: "First Seat", 2: "Second Seat", 3: "Third Seat"}
    return position_map[seat]


def simulate_hand(
    hand: list[int],
    upcard: int,
    seat: int,
    suit: int = None,
    alone: bool = False,
    strategies: list[Strategy] = None,
    split_by_maker: bool = False,
    trials: int = 50_000,
    seed: int = None,
    verbose: bool = False,
):
    """
    seat of 0 is dealer
    """
    stats = SimulationStats(split_by_maker=split_by_maker)
    rng = random.Random(seed)

    if strategies is None:
        strategies = [SimpleStrategy() for _ in range(4)]

    for i in range(trials):
        game = EuchreGame(strategies=strategies, verbose=verbose)

        outcome = game.play_hand(True, hand, upcard, seat, suit, alone, rng)
        stats.record(outcome)

    return stats.report()


def simulate_choices(
    hand: list[int],
    upcard: int,
    seat: int,
    strategies: list[Strategy] = None,
    split_by_maker: bool = False,
    trials: int = 50_000,
    seed: int = None,
    verbose: bool = False,
):
    suits = [0, 1, 2, 3, -1]  # All suits and pass
    alones = [False, True]
    results = []
    for suit in suits:
        suit_str = SUITS[suit] if suit != -1 else "Pass"
        for alone in alones:
            # Dealer can't pass in the second round, so no reason to simulate this
            if seat == 0 and suit == -1:
                continue
            result = simulate_hand(
                hand,
                upcard,
                seat,
                suit,
                alone,
                strategies,
                split_by_maker,
                trials,
                seed,
                verbose,
            )
            base = {"suit_choice": suit_str, "alone_choice": alone}
            rows = result if isinstance(result, list) else [result]
            results.extend(base | row for row in rows)
    return results


def simulate_choices_test_bad(
    hand: list[int],
    upcard: int,
    seat: int,
    strategies: list[Strategy],
    suits: list[int] = [0, 1, 2, 3, -1],  # All suits and pass
    alones: list[bool] = [False, True],
    trials: int = 50_000,
    rng_seed: int = 42,
    verbose: bool = False,
):
    """
    Runs simulations efficiently:
      - One baseline run to capture Maker=False
      - One run per (suit, alone) to capture Maker=True
    """

    results = []

    # ------------------------------------------------------------------
    # 1) Baseline simulation: natural bidding (captures Maker=False once)
    # ------------------------------------------------------------------
    baseline = simulate_hand(
        hand=hand,
        upcard=upcard,
        seat=seat,
        suit=None,
        alone=None,
        strategies=strategies,
        split_by_maker=True,
        trials=trials,
        rng_seed=rng_seed,
        verbose=verbose,
    )

    baseline_defender = next(r for r in baseline if r["Maker"] is False)

    # ------------------------------------------------------------------
    # 2) Forced simulations: capture Maker=True only
    # ------------------------------------------------------------------
    for suit in suits:
        # Dealer cannot pass
        if seat == 0 and suit == -1:
            continue

        suit_choice_str = SUITS[suit] if suit != -1 else "Pass"

        for alone in alones:
            forced = simulate_hand(
                hand=hand,
                upcard=upcard,
                seat=seat,
                suit=suit,
                alone=alone,
                strategies=strategies,
                split_by_maker=True,
                trials=trials,
                rng_seed=rng_seed,
                verbose=verbose,
            )

            maker_row = next(r for r in forced if r["Maker"] is True)

            results.append(
                {
                    "Maker": True,
                    "suit_choice": suit_choice_str,
                    "alone_choice": alone,
                    **maker_row,
                }
            )

    # ------------------------------------------------------------------
    # 3) Append defender row exactly once
    # ------------------------------------------------------------------
    results.append(
        {
            "Maker": False,
            "suit_choice": "—",
            "alone_choice": "—",
            **baseline_defender,
        }
    )

    return results


def best_trump_choice(results: list[dict], metric: str) -> dict:
    """
    Return the result dict that maximizes the given metric.

    Parameters
    ----------
    results : list[dict]
        Simulation results.
    metric : str
        Metric to maximize (e.g. 'avg_points' or 'win_rate').

    Returns
    -------
    dict
        The result entry with the highest metric value.
    """
    if not results:
        raise ValueError("results is empty")

    if metric not in results[0]:
        raise ValueError(f"Metric '{metric}' not found in results")

    return max(results, key=lambda r: r[metric])


def simulate_second_round_trump_choice(
    hand: list[int],
    upcard: int,
    seat: int,
    strategies: list[Strategy] = None,
    trials: int = 50_000,
    seed: int = None,
    verbose: bool = False,
    metric: str = "avg_points",  # Could also be win_rate
    verbose_sim: bool = True,
):
    if verbose_sim:
        print("=== SIMULATING SECOND-ROUND TRUMP CALL ===")
        print(f"Position: {position_str_from_seat(seat)}")
        print(f"Hand: {[CARD_NAME[card] for card in hand]}")
        print(f"Upcard: {CARD_NAME[upcard]}")
        print(f"Objective: {metric}")
        print(
            "\n*Note that results include hands where someone else called trump before we could, so metrics are as of being dealt the hand (before any other actions)*"
        )
        print(
            "*This is fine since all results include these same hands, but it means that these metrics are only useful in a relative comparison (i.e. this is not true EV as of the time you'd be calling)*"
        )

    upcard_suit = card_suit(upcard)
    remaining_suits = [s for s in range(4) if s != upcard_suit]
    pass_suit = -1

    # Every remaining suit × {not alone, alone}
    suit_alones = [(suit, alone) for suit in remaining_suits for alone in (False, True)]

    # Add pass option only if allowed (non-dealer)
    if seat != 0:
        suit_alones.append((pass_suit, None))

    results = []
    for suit, alone in suit_alones:
        suit_str = SUITS[suit] if suit != -1 else "Pass"

        result = simulate_hand(
            hand,
            upcard,
            seat,
            suit,
            alone,
            strategies,
            False,
            trials,
            seed,
            verbose,
        )
        base = {"suit_choice": suit_str, "alone_choice": alone}
        rows = result if isinstance(result, list) else [result]
        results.extend(base | row for row in rows)
    return results


def simulate_first_round_trump_choice(
    hand: list[int],
    upcard: int,
    seat: int,
    strategies: list[Strategy] = None,
    trials: int = 50_000,
    seed: int = None,
    verbose: bool = False,
    metric: str = "avg_points",  # Could also be win_rate
):
    print("=== SIMULATING FIRST-ROUND TRUMP CALL ===")
    print(f"Position: {position_str_from_seat(seat)}")
    print(f"Hand: {[CARD_NAME[card] for card in hand]}")
    print(f"Upcard: {CARD_NAME[upcard]}")
    print(f"Objective: {metric}")
    print(
        "\n*Note that results include hands where someone else called trump before we could, so metrics are as of being dealt the hand (before any other actions)*"
    )
    print(
        "*This is fine since all results include these same hands, but it means that these metrics are only useful in a relative comparison (i.e. this is not true EV as of the time you'd be calling)*"
    )

    upcard_suit = card_suit(upcard)

    # First-round options: upcard suit × {not alone, alone}
    first_round_choices = [(upcard_suit, alone) for alone in (False, True)]

    # If we pass in round 1, assume optimal second-round play
    second_round_results = simulate_second_round_trump_choice(
        hand, upcard, seat, strategies, trials, seed, verbose, metric, False
    )
    best_pass_result = best_trump_choice(second_round_results, metric)

    results = []
    for suit, alone in first_round_choices:
        result = simulate_hand(
            hand,
            upcard,
            seat,
            suit,
            alone,
            strategies,
            False,
            trials,
            seed,
            verbose,
        )

        choice_label = "Alone" if alone else "Not Alone"
        base = {"choice": choice_label}

        rows = result if isinstance(result, list) else [result]
        results.extend(base | row for row in rows)

    # Add the "Pass" option, using best second-round outcome
    pass_row = {
        "choice": "Pass",
        **{
            k: v
            for k, v in best_pass_result.items()
            if k not in ("suit_choice", "alone_choice")
        },
    }
    results.append(pass_row)

    return results


# Example CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split-maker",
        action="store_true",
        help="Split results by whether player was the maker",
    )
    parser.add_argument("--trials", type=int, default=50000)
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--metric",
        choices=("avg_points", "win_rate"),
        default="avg_points",
        help="Metric to maximize when selecting best trump choice",
    )

    args = parser.parse_args()

    # hand_str = ["Jc", "Js", "Jh", "Jd", "9d"]
    # upcard_str = "9h"
    # hand_str = ["9c", "Tc", "Jc", "Qc", "Kc"]
    # upcard_str = "Ac"
    hand_str = ["Jc", "Ac", "9c", "Ah", "Qd"]
    upcard_str = "9h"
    seat = 1
    # seat = 1
    # seat = 2
    # seat = 3

    # my_strat = PassiveStrategy()
    my_strat = SimpleStrategy()
    # others_strats = [PassiveStrategy() for _ in range(3)]
    others_strats = [SimpleStrategy() for _ in range(3)]

    hand = card_int(hand_str)
    upcard = card_int(upcard_str)

    strategies = others_strats.copy()
    strategies.insert(seat, my_strat)

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
        hand,
        upcard,
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
    alones = [False, True]
    suits = suit_int(force_suit_names)

    # Collect results for all combinations
    """results = simulate_choices(
        hand,
        upcard,
        seat,
        strategies,
        args.split_maker,
        args.trials,
        args.seed,
        args.verbose,
    )"""
    """results = simulate_choices_test_bad(
        hand,
        upcard,
        seat,
        strategies,
        suits,
        alones,
        args.trials,
        args.seed,
        args.verbose,
    )"""

    """results = simulate_second_round_trump_choice(
        hand,
        upcard,
        seat,
        strategies,
        args.trials,
        args.seed,
        args.verbose,
        args.metric,
        True,
    )"""
    results = simulate_first_round_trump_choice(
        hand,
        upcard,
        seat,
        strategies,
        args.trials,
        args.seed,
        args.verbose,
        args.metric,
    )
    # Print results as a table
    # print(tabulate(results, headers="keys", tablefmt="grid"))
    pd.set_option("display.float_format", "{:.3f}".format)
    results_df = pd.DataFrame(results).sort_values(args.metric, ascending=False)
    print("\n=== RESULTS ===")
    print(results_df)
