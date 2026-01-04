import random
from typing import Callable

from game import EuchreGame, SimpleStrategy

"""
simulation.py — Monte Carlo hand simulations for Euchre EV
"""


class SimulationStats:
    def __init__(self):
        self.count = 0
        self.tricks = 0
        self.points = 0
        self.wins = 0

    def record(self, outcome: dict):
        self.count += 1
        self.tricks += outcome["tricks"]
        self.points += outcome["points"]
        if outcome["is_win"]:
            self.wins += 1

    def report(self):
        return {
            "count": self.count,
            "avg_tricks": self.tricks / self.count if self.count else 0,
            "avg_points": self.points / self.count if self.count else 0,
            "win_rate": self.wins / self.count if self.count else 0,
        }


def simulate_hand(
    fixed_hand: list[int],
    fixed_upcard: int,
    fixed_seat: int,
    trials: int,
    call_override: Callable = None,
    rng_seed: int = None,
    verbose: bool = False,
):
    """
    fixed_seat of 0 is dealer
    """
    stats = SimulationStats()
    rng = random.Random(rng_seed)

    for i in range(trials):
        game = EuchreGame(
            strategies=[SimpleStrategy() for _ in range(4)], verbose=verbose
        )
        """# override call_trump method if provided
        DOESN'T WORK AT THE MOMENT. WOULD NEED TO ADD LOGIC IN strategy.py
        if call_override:
            for strat in game.strategies:
                strat.choose_trump = call_override"""

        # Adjust fixed_seat relative to the dealer
        relative_seat = (fixed_seat + game.dealer) % 4

        outcome = game.play_hand(True, fixed_hand, fixed_upcard, relative_seat, rng)
        stats.record(outcome)

    return stats.report()


# Example CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=50000)
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # Example card IDs — replace with actual Euchre constants
    hand = [0, 1, 2, 3, 4]
    upcard = 5
    seat = 0

    """print("Simulate calling trump always")
    report_call = simulate_hand(
        example_hand,
        example_upcard,
        fixed_seat=0,
        trials=args.trials,
        # call_override=lambda *a, **k: (0, False),
        call_override=lambda *a, **k: None,
        rng_seed=42,
    )
    print(report_call)"""

    # print("Simulate passing always")
    report_pass = simulate_hand(
        hand, upcard, seat, args.trials, lambda *a, **k: None, args.seed, args.verbose
    )
    print(report_pass)
