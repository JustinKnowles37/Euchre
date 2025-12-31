import random
from cards import RANKS, SUITS, card_name, card_suit
from rules import winner_of_trick, legal_moves
from strategy import SimpleStrategy  # Strategy class with choose_trump + play_card

NUM_PLAYERS = 4
HAND_SIZE = 5


def log(msg):
    print(f"[CALL_TRUMP] {msg}")


class EuchreGame:
    def __init__(self, players=None, strategies=None):
        self.deck = list(range(24))
        self.players = players or ["North", "East", "South", "West"]

        # strategy objects for each player
        self.strategies = (
            strategies
            if strategies is not None
            else [SimpleStrategy() for _ in range(4)]
        )

        self.hands = [[] for _ in range(NUM_PLAYERS)]
        self.trump = None
        self.upcard = None
        self.scores = [0, 0]  # team 0 = players 0 & 2, team 1 = players 1 & 3
        self.dealer = 0
        self.going_alone = False
        self.loner = None
        self.sitting_out = None
        self.defending_alone = False
        self.defender_loner = None
        self.two_player_hand = False  # True if maker and defender both go alone

    # ------------------------------------------------------------
    # SHUFFLE + DEAL
    # ------------------------------------------------------------
    def shuffle_and_deal(self):
        random.shuffle(self.deck)
        self.hands = [
            self.deck[i * HAND_SIZE : (i + 1) * HAND_SIZE] for i in range(NUM_PLAYERS)
        ]
        self.upcard = self.deck[NUM_PLAYERS * HAND_SIZE]

    # ------------------------------------------------------------
    # TRUMP CALLING (each player's strategy decides)
    # ------------------------------------------------------------
    def call_trump(self):
        """
        Handles both rounds of trump calling with correct rotation.
        Supports going alone.
        """
        print("\n=== CALLING TRUMP PHASE ===")
        print(f"Upcard is {card_name(self.upcard)}\n")

        # Reset loner state every hand
        self.going_alone = False
        self.loner = None
        self.sitting_out = None
        self.defending_alone = False
        self.defender_loner = None
        self.two_player_hand = False

        start_player = (self.dealer + 1) % 4
        upcard_suit = card_suit(self.upcard)

        # ----------------------------
        # FIRST ROUND: ordering up
        # ----------------------------
        for offset in range(4):
            i = (start_player + offset) % 4
            strat = self.strategies[i]
            hand = self.hands[i]
            is_dealer = i == self.dealer
            upcard_visible = self.upcard if is_dealer else None

            log(
                f"{self.players[i]} {'(DEALER)' if is_dealer else ''} hand: "
                + ", ".join(card_name(c) for c in hand)
            )

            result = strat.choose_trump(
                hand=hand,
                upcard=upcard_visible,
                is_dealer=is_dealer,
                valid_suits=[upcard_suit],
            )

            if upcard_visible is not None:
                log(f"{self.players[i]} sees upcard {card_name(self.upcard)}")

            if result is None:
                log(f"{self.players[i]} passes")
                continue

            # --- DEALER PICKS UP UP-CARD (ROUND 1 ONLY) ---
            dealer = self.dealer
            dealer_hand = self.hands[dealer]

            # Dealer takes the upcard
            dealer_hand.append(self.upcard)

            # Dealer discards one card
            discard = self.strategies[dealer].discard(dealer_hand, self.trump)
            dealer_hand.remove(discard)

            print(
                f"{self.players[dealer]} picks up {card_name(self.upcard)} "
                f"and discards {card_name(discard)}"
            )

            assert len(dealer_hand) == 5
            # --------------------------------------------

            suit, alone = result

            self.trump = suit
            self.makers = i % 2
            self.going_alone = alone
            self.loner = i
            self.sitting_out = (i + 2) % 4 if alone else None

            log(
                f"{self.players[i]} CALLS TRUMP → {SUITS[suit]}"
                + (" AND GOES ALONE" if alone else "")
            )

            print(
                f"\nTrump set to {SUITS[self.trump]} by {self.players[i]} "
                f"(Team {self.makers})\n"
            )
            return

        # ----------------------------
        # SECOND ROUND: call another suit
        # ----------------------------
        remaining_suits = [s for s in range(4) if s != upcard_suit]

        for offset in range(4):
            i = (start_player + offset) % 4
            strat = self.strategies[i]
            hand = self.hands[i]

            result = strat.choose_trump(
                hand=hand,
                is_dealer=(i == self.dealer),
                valid_suits=remaining_suits,
            )

            if result is None:
                log(f"{self.players[i]} passes in second round")
                continue

            suit, alone = result

            self.trump = suit
            self.makers = i % 2
            self.going_alone = alone
            self.loner = i
            self.sitting_out = (i + 2) % 4 if alone else None

            log(
                f"{self.players[i]} CALLS TRUMP → {SUITS[suit]} in second round"
                + (" AND GOES ALONE" if alone else "")
            )

            print(
                f"\nTrump set to {SUITS[self.trump]} by {self.players[i]} "
                f"(Team {self.makers})\n"
            )
            return

        # ----------------------------
        # DEALER FORCED PICK
        # ----------------------------
        dealer = self.dealer
        strat = self.strategies[dealer]

        suit, alone = strat.choose_trump(
            hand=self.hands[dealer],
            valid_suits=remaining_suits,
            force=True,
        )

        self.trump = suit
        self.makers = dealer % 2
        self.going_alone = alone
        self.loner = dealer
        self.sitting_out = (dealer + 2) % 4 if alone else None

        log(
            f"Dealer {self.players[dealer]} forced to choose trump → {SUITS[suit]}"
            + (" AND GOES ALONE" if alone else "")
        )

        print(
            f"\nFinal Trump: {SUITS[self.trump]} " f"(Team {self.makers} are makers)\n"
        )

    def check_defend_alone(self):
        """
        Allow defender to go alone only if maker went alone.
        """
        # Must already be a maker-alone hand
        if not self.going_alone:
            return

        makers_team = self.makers
        defenders = [i for i in range(4) if i % 2 != makers_team]

        for p in defenders:
            if self.strategies[p].defend_alone(self.hands[p], self.trump):
                self.defending_alone = True
                self.defender_loner = p

                # Mark sitting out players
                self.sitting_out = (self.loner + 2) % 4  # maker partner
                self.defender_sitting_out = (p + 2) % 4  # defender partner

                self.two_player_hand = True

                print(
                    f"{self.players[p]} DEFENDS ALONE! "
                    f"Only two players active: {self.players[self.loner]} vs {self.players[p]}"
                )
                return

    # ------------------------------------------------------------
    # PLAY A TRICK
    # ------------------------------------------------------------
    def play_trick(self, lead_player):
        trick = []
        players_in_trick = []

        for offset in range(NUM_PLAYERS):
            p = (lead_player + offset) % NUM_PLAYERS

            # Skip anyone sitting out
            if p == self.sitting_out:
                continue
            if self.two_player_hand and p == self.defender_sitting_out:
                continue

            players_in_trick.append(p)

            hand = self.hands[p]
            strat = self.strategies[p]

            led_card = trick[0] if trick else None
            lm = legal_moves(hand, led_card, self.trump)

            card = strat.play_card(hand, lm, trick, self.trump)
            hand.remove(card)
            trick.append(card)

            print(f"{self.players[p]} plays {card_name(card)}")

        led_suit = card_suit(trick[0])
        winner_offset = winner_of_trick(trick, self.trump, led_suit)
        winner = players_in_trick[winner_offset]

        print(f"{self.players[winner]} wins the trick\n")
        return winner

    def first_active_player(self, start):
        """
        Return the first player > start who is not sitting out.
        """
        for offset in range(1, NUM_PLAYERS + 1):  # start at next seat
            p = (start + offset) % NUM_PLAYERS
            if p == self.sitting_out:
                continue
            if self.two_player_hand and p == self.defender_sitting_out:
                continue
            return p
        return start  # fallback

    # ------------------------------------------------------------
    # PLAY ONE HAND (5 TRICKS)
    # ------------------------------------------------------------
    def play_hand(self):
        self.shuffle_and_deal()
        self.call_trump()
        self.check_defend_alone()

        print(f"Trump is {SUITS[self.trump]}")

        lead_player = self.first_active_player(self.dealer)
        tricks_won = [0, 0]  # team 0, team 1

        for _ in range(HAND_SIZE):
            winner = self.play_trick(lead_player)

            team = winner % 2
            tricks_won[team] += 1
            lead_player = winner

        makers = self.makers
        defenders = 1 - makers
        maker_tricks = tricks_won[makers]

        # scoring logic
        if self.going_alone:
            if maker_tricks == 5:
                # Lone hand sweep
                self.scores[makers] += 4
                print(f"{self.players[self.loner]} wins ALL 5 tricks alone! +4 points")
            elif maker_tricks >= 3:
                # Lone hand win (but not sweep)
                self.scores[makers] += 1
                print(f"{self.players[self.loner]} wins the hand alone! +1 point")
            else:
                if self.two_player_hand:
                    # Lone defender win
                    self.scores[defenders] += 4
                    print(
                        f"{self.players[self.defender_loner]} DEFENDS ALONE successfully! +4 points"
                    )
                else:
                    # Lone hand euchred
                    self.scores[defenders] += 2
                    print(
                        f"{self.players[self.loner]} was euchred while going alone! Defenders +2"
                    )
        else:
            # Normal (non-loner) scoring
            if maker_tricks < 3:
                self.scores[defenders] += 2
                print(f"Team {defenders} euchred the makers! +2")
            elif maker_tricks == 5:
                self.scores[makers] += 2
                print(f"Team {makers} sweeps! +2")
            else:
                self.scores[makers] += 1
                print(f"Team {makers} wins the hand! +1")

        print(f"Score: Team 0 = {self.scores[0]}, Team 1 = {self.scores[1]}\n")

    # ------------------------------------------------------------
    # FULL GAME LOOP
    # ------------------------------------------------------------
    def play_game(self, winning_score=10):
        while max(self.scores) < winning_score:
            print(f"Dealer is {self.players[self.dealer]}")
            self.play_hand()
            self.dealer = (self.dealer + 1) % NUM_PLAYERS

        winner = 0 if self.scores[0] >= winning_score else 1
        print(f"*** Team {winner} wins the game! ***")


# ------------------------------------------------------------
# STANDALONE TEST
# ------------------------------------------------------------
if __name__ == "__main__":
    print("Starting Euchre test game...\n")

    strategies = [SimpleStrategy() for _ in range(4)]
    game = EuchreGame(
        players=["North", "East", "South", "West"],
        strategies=strategies,
    )
    game.play_game(winning_score=10)

    print("\nFinal Score:")
    print(f"Team 0: {game.scores[0]}")
    print(f"Team 1: {game.scores[1]}")
    print("Game complete.")
