"""
simulation.py — Monte Carlo hand simulations for Euchre EV
"""

import argparse
import random
from dataclasses import dataclass
from typing import Optional, List

import pandas as pd

from cards import card_int, CARD_NAME, card_suit, SUITS
from game import EuchreGame
from strategy import *


# =========================
# Constants
# =========================

PASS_SUIT = -1
POINT_VALUES = (-4, -2, -1, 1, 2, 4)


# =========================
# Configuration
# =========================


@dataclass(frozen=True)
class SimulationConfig:
    trials: int = 50_000
    seed: Optional[int] = None
    verbose: bool = False
    split_by_maker: bool = False
    strategies: Optional[List[Strategy]] = None


# =========================
# Stats
# =========================


class SimulationStats:
    def __init__(self, split_by_maker: bool = False):
        self.split_by_maker = split_by_maker

        if split_by_maker:
            self.by_maker = {
                True: SimulationStats(False),
                False: SimulationStats(False),
            }
            return

        self.trials = 0
        self.tricks = 0
        self.points = 0
        self.wins = 0
        self.point_counts = {p: 0 for p in POINT_VALUES}

    def record(self, outcome: dict):
        if self.split_by_maker:
            self.by_maker[outcome["is_maker"]].record(outcome)
            return

        points = outcome["points"]
        self.trials += 1
        self.tricks += outcome["tricks"]
        self.points += points
        self.wins += int(outcome["is_win"])
        self.point_counts[points] += 1

    def report(self):
        if self.split_by_maker:
            rows = []
            for maker, stats in self.by_maker.items():
                rows.append({"Maker": maker, **stats.report()})
            return rows

        trials = self.trials or 1
        return {
            "trials": self.trials,
            "avg_tricks": self.tricks / trials,
            "avg_points": self.points / trials,
            "win_rate": self.wins / trials,
            **{f"p_{p}": self.point_counts[p] / trials for p in POINT_VALUES},
        }


# =========================
# Printing
# =========================


def print_experiment_header(
    *,
    experiment: str,
    hand: list[int],
    upcard: int,
    seat: int,
    metric: str,
):
    print("=== SIMULATING TRUMP DECISION ===")
    print(f"Experiment: {experiment}")
    print(f"Position: {position_str_from_seat(seat)}")
    print(f"Hand: {hand_to_str(hand)}")
    print(f"Upcard: {CARD_NAME[upcard]}")
    print(f"Objective: {metric}")

    print(
        "\n*Note: Results include hands where another player may have called trump "
        "before your decision point. Metrics are therefore conditional on being "
        "dealt this hand, and are best used for relative comparisons.*\n"
    )


# =========================
# Utilities
# =========================


def position_str_from_seat(seat: int) -> str:
    position_map = {
        0: "Dealer",
        1: "First Seat",
        2: "Second Seat",
        3: "Third Seat",
    }
    if seat not in position_map:
        raise ValueError(f"Invalid seat: {seat}")
    return position_map[seat]


def suit_label(suit: int) -> str:
    return SUITS[suit] if suit != PASS_SUIT else "Pass"


def hand_to_str(hand: list[int]) -> str:
    return ", ".join(str(CARD_NAME[card]) for card in hand)


# =========================
# Choice generators
# =========================


def first_round_choices(upcard_suit: int):
    return [(upcard_suit, False), (upcard_suit, True), (PASS_SUIT, None)]


def second_round_choices(upcard_suit: int, seat: int):
    remaining = [s for s in range(4) if s != upcard_suit]
    choices = [(s, a) for s in remaining for a in (False, True)]
    if seat != 0:
        choices.append((PASS_SUIT, None))
    return choices


# =========================
# Core simulation engine
# =========================


def simulate_hand(
    hand: list[int],
    upcard: int,
    seat: int,
    suit: Optional[int],
    alone: Optional[bool],
    config: SimulationConfig,
):
    stats = SimulationStats(split_by_maker=config.split_by_maker)
    rng = random.Random(config.seed)

    strategies = (
        config.strategies
        if config.strategies is not None
        else [SimpleStrategy() for _ in range(4)]
    )

    for _ in range(config.trials):
        game = EuchreGame(strategies=strategies, verbose=config.verbose)
        outcome = game.play_hand(True, hand, upcard, seat, suit, alone, rng)
        stats.record(outcome)

    return stats.report()


# =========================
# Experiment helpers
# =========================


def run_choices(hand, upcard, seat, choices, config):
    results = []
    for suit, alone in choices:
        result = simulate_hand(hand, upcard, seat, suit, alone, config)
        base = {
            "suit_choice": suit_label(suit),
            "alone_choice": alone,
        }
        rows = result if isinstance(result, list) else [result]
        results.extend(base | row for row in rows)
    return results


def best_trump_choice(results: list[dict], metric: str) -> dict:
    if not results:
        raise ValueError("results is empty")
    if metric not in results[0]:
        raise ValueError(f"Metric '{metric}' not found")
    return max(results, key=lambda r: r[metric])


# =========================
# Experiments
# =========================


def simulate_all_choices(hand, upcard, seat, config: SimulationConfig):
    suits = [0, 1, 2, 3, PASS_SUIT]
    alones = [False, True]

    choices = []
    for suit in suits:
        for alone in alones:
            if seat == 0 and suit == PASS_SUIT:
                continue
            choices.append((suit, alone))

    return run_choices(hand, upcard, seat, choices, config)


def simulate_second_round_trump_choice(hand, upcard, seat, config: SimulationConfig):
    upcard_suit = card_suit(upcard)
    choices = second_round_choices(upcard_suit, seat)
    return run_choices(hand, upcard, seat, choices, config)


def simulate_first_round_trump_choice(hand, upcard, seat, config: SimulationConfig):
    upcard_suit = card_suit(upcard)
    return run_choices(hand, upcard, seat, first_round_choices(upcard_suit), config)


# =========================
# CLI
# =========================

EXPERIMENTS = {
    "all": simulate_all_choices,
    "first": simulate_first_round_trump_choice,
    "second": simulate_second_round_trump_choice,
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", choices=EXPERIMENTS, required=True)
    parser.add_argument("--trials", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--split-maker", action="store_true")
    parser.add_argument(
        "--metric",
        choices=("avg_points", "win_rate"),
        default="avg_points",
    )

    args = parser.parse_args()

    # Example setup
    hand_str = ["Jc", "Ac", "9c", "Ah", "Qd"]
    upcard_str = "9h"
    seat = 1  # 0 is dealer

    my_strat = SimpleStrategy()
    others = [SimpleStrategy() for _ in range(3)]

    hand = card_int(hand_str)
    upcard = card_int(upcard_str)

    strategies = others.copy()
    strategies.insert(seat, my_strat)

    print_experiment_header(
        experiment=args.experiment,
        hand=hand,
        upcard=upcard,
        seat=seat,
        metric=args.metric,
    )

    config = SimulationConfig(
        trials=args.trials,
        seed=args.seed,
        verbose=args.verbose,
        split_by_maker=args.split_maker,
        strategies=strategies,
    )

    experiment_fn = EXPERIMENTS[args.experiment]
    results = experiment_fn(hand, upcard, seat, config)

    pd.set_option("display.float_format", "{:.3f}".format)
    df = pd.DataFrame(results).sort_values(args.metric, ascending=False)
    print(df)
