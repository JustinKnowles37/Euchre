import random
from typing import Callable

from game import EuchreGame, SimpleStrategy

"""
simulation.py — Monte Carlo hand simulations for Euchre EV
"""


class SimulationStats:
    def __init__(self):
        self.count = 0
        self.maker_points = 0
        self.tricks_makers = 0
        self.tricks_defenders = 0
        self.loner_success = 0

    def record(self, outcome: dict):
        self.count += 1
        self.maker_points += outcome["maker_points"]
        self.tricks_makers += outcome["tricks_makers"]
        self.tricks_defenders += outcome["tricks_defenders"]
        if outcome["loner_success"]:
            self.loner_success += 1

    def report(self):
        return {
            "count": self.count,
            "avg_maker_points": self.maker_points / self.count if self.count else 0,
            "avg_maker_tricks": self.tricks_makers / self.count if self.count else 0,
            "avg_defender_tricks": (
                self.tricks_defenders / self.count if self.count else 0
            ),
            "loner_success_rate": self.loner_success / self.count if self.count else 0,
        }


def simulate_hand(
    fixed_hand: list[int],
    fixed_upcard: int,
    fixed_seat: int,
    trials: int,
    call_override: Callable = None,
    rng_seed: int = None,
):
    stats = SimulationStats()
    rng = random.Random(rng_seed)

    for i in range(trials):
        game = EuchreGame(strategies=[SimpleStrategy() for _ in range(4)])
        """# override call_trump method if provided
        DOESN'T WORK AT THE MOMENT. WOULD NEED TO ADD LOGIC IN strategy.py
        if call_override:
            for strat in game.strategies:
                strat.choose_trump = call_override"""

        outcome = game.play_hand(True, fixed_hand, fixed_upcard, fixed_seat, rng)
        stats.record(outcome)

    return stats.report()


# Example CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=50000)
    args = parser.parse_args()

    # Example card IDs — replace with actual Euchre constants
    example_hand = [0, 1, 2, 3, 4]
    example_upcard = 5

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
        example_hand,
        example_upcard,
        fixed_seat=0,
        trials=args.trials,
        call_override=lambda *a, **k: None,
        rng_seed=42,
    )
    print(report_pass)
