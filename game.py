import random
from cards import SUITS, card_name, card_suit
from rules import winner_of_trick, legal_moves
from strategy import SimpleStrategy

NUM_PLAYERS = 4
HAND_SIZE = 5


class EuchreGame:
    def __init__(self, players=None, strategies=None, verbose=False):
        self.deck = list(range(24))
        self.players = players or ["North", "East", "South", "West"]

        # strategy objects for each player
        self.strategies = (
            strategies
            if strategies is not None
            else [SimpleStrategy() for _ in range(4)]
        )

        # only prints if verbose==True
        if verbose:
            self.log = print
        else:
            self.log = lambda *args, **kwargs: None

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

    def deal_fixed_hand(
        self,
        fixed_hand: list[int],
        fixed_upcard: int,
        fixed_seat: int,
        rng: random.Random,
    ):
        """
        Replace normal dealing with a fixed hand for one player and fixed upcard.
        All other cards are shuffled and dealt around that.
        """
        # Remove fixed cards from deck
        remaining = [c for c in self.deck if c not in fixed_hand and c != fixed_upcard]

        # Shuffle the remainder
        rng.shuffle(remaining)

        # Build hands
        self.hands = [[] for _ in range(NUM_PLAYERS)]
        # assign fixed hand
        self.hands[fixed_seat] = list(fixed_hand)

        # assign others
        idx = 0
        for p in range(NUM_PLAYERS):
            if p == fixed_seat:
                continue
            # deal HAND_SIZE cards to others
            self.hands[p] = remaining[idx : idx + HAND_SIZE]
            idx += HAND_SIZE

        # fixed upcard sits after dealing
        self.upcard = fixed_upcard

    # ------------------------------------------------------------
    # TRUMP CALLING (each player's strategy decides)
    # ------------------------------------------------------------
    def call_trump(self, fixed_seat, force_suit_choice, force_alone_choice):
        """
        Handles both rounds of trump calling with correct rotation.
        Supports going alone.
        """
        self.log("\n=== CALLING TRUMP PHASE ===")
        self.log(f"Upcard is {card_name(self.upcard)}\n")

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

            is_fixed_seat = fixed_seat == (offset + 1) % 4
            is_forced_to_pass = (
                is_fixed_seat
                and force_suit_choice is not None
                and force_suit_choice != upcard_suit
            )
            is_forced_to_call_suit = is_fixed_seat and force_suit_choice == upcard_suit
            is_forced_alone_choice = is_fixed_seat and force_alone_choice is not None

            self.log(
                f"[CALL_TRUMP] {self.players[i]} {'(DEALER)' if is_dealer else ''} hand: "
                + ", ".join(card_name(c) for c in hand)
            )

            if is_forced_to_pass:
                self.log(
                    f"[CALL_TRUMP] {self.players[i]} is forced to pass in the first round"
                )
                continue

            if upcard_visible is not None:
                self.log(
                    f"[CALL_TRUMP] {self.players[i]} sees upcard {card_name(self.upcard)}"
                )

            result = strat.choose_trump_first_round(
                hand=hand,
                upcard=self.upcard,
                is_dealer=is_dealer,
                valid_suits=[upcard_suit],
            )

            # If forced to call trump here, force that result, keeping the strategy's loner logic
            # We still always need to run strat.choose_trump_first_round() to determine loner decision
            if is_forced_to_call_suit:
                # result[1] only works since we know they could only call alone on upcard_suit
                result = (upcard_suit, result[1] if result is not None else False)
                self.log(
                    f"[CALL_TRUMP] {self.players[i]} was forced to call {SUITS[upcard_suit]}"
                )

            # If going alone is forced to True/False and we want to call at all, force that result
            if is_forced_alone_choice and result is not None:
                result = (result[0], force_alone_choice)
                self.log(
                    f"[CALL_TRUMP] {self.players[i]} was forced {'to go alone' if force_alone_choice else 'not to go alone'}"
                )

            if result is None:
                self.log(f"[CALL_TRUMP] {self.players[i]} passes")
                continue

            # --- DEALER PICKS UP UP-CARD (ROUND 1 ONLY) ---
            dealer = self.dealer
            dealer_hand = self.hands[dealer]
            self.turned_down_card = None

            # Dealer takes the upcard
            dealer_hand.append(self.upcard)

            # Dealer discards one card
            discard = self.strategies[dealer].discard(dealer_hand, self.trump)
            dealer_hand.remove(discard)

            self.log(
                f"[CALL_TRUMP] {self.players[dealer]} picks up {card_name(self.upcard)} "
                f"and discards {card_name(discard)}"
            )

            assert len(dealer_hand) == 5
            # --------------------------------------------

            suit, alone = result

            self.trump = suit
            self.call_round = 1
            self.maker = i
            self.makers = i % 2
            self.going_alone = alone
            self.loner = i
            self.sitting_out = (i + 2) % 4 if alone else None

            self.log(
                f"[CALL_TRUMP] {self.players[i]} CALLS TRUMP → {SUITS[suit]}"
                + (" AND GOES ALONE" if alone else "")
            )

            self.log(
                f"\nTrump set to {SUITS[self.trump]} by {self.players[i]} "
                f"(Team {self.makers})\n"
            )
            return

        # ----------------------------
        # SECOND ROUND: call another suit
        # ----------------------------
        remaining_suits = [s for s in range(4) if s != upcard_suit]
        self.turned_down_card = self.upcard
        self.call_round = 2

        for offset in range(3):
            i = (start_player + offset) % 4
            strat = self.strategies[i]
            hand = self.hands[i]

            is_fixed_seat = fixed_seat == (offset + 1) % 4
            is_forced_to_pass = is_fixed_seat and force_suit_choice == -1
            is_forced_to_call_suit = (
                is_fixed_seat and force_suit_choice in remaining_suits
            )
            is_forced_alone_choice = is_fixed_seat and force_alone_choice is not None

            if is_forced_to_pass:
                self.log(
                    f"[CALL_TRUMP] {self.players[i]} is forced to pass in the second round"
                )
                continue

            result = strat.choose_trump_second_round(
                hand=hand,
                turned_down_card=self.turned_down_card,
                valid_suits=(
                    [force_suit_choice] if is_forced_to_call_suit else remaining_suits
                ),
            )

            # If forced to call trump here, force that result, keeping the strategy's loner logic
            # We still always need to run strat.choose_trump_second_round() to determine loner decision
            if is_forced_to_call_suit:
                # result[1] only works since we know they could only call alone on force_suit_choice
                result = (force_suit_choice, result[1] if result is not None else False)
                self.log(
                    f"[CALL_TRUMP] {self.players[i]} was forced to call {SUITS[force_suit_choice]}"
                )

            # If going alone is forced to True/False and we want to call at all, force that result
            if is_forced_alone_choice and result is not None:
                result = (result[0], force_alone_choice)
                self.log(
                    f"[CALL_TRUMP] {self.players[i]} was forced {'to go alone' if force_alone_choice else 'not to go alone'}"
                )

            if result is None:
                self.log(f"[CALL_TRUMP] {self.players[i]} passes in second round")
                continue

            suit, alone = result

            self.trump = suit
            self.maker = i
            self.makers = i % 2
            self.going_alone = alone
            self.loner = i
            self.sitting_out = (i + 2) % 4 if alone else None

            self.log(
                f"[CALL_TRUMP] {self.players[i]} CALLS TRUMP → {SUITS[suit]} in second round"
                + (" AND GOES ALONE" if alone else "")
            )

            self.log(
                f"\nTrump set to {SUITS[self.trump]} by {self.players[i]} "
                f"(Team {self.makers})\n"
            )
            return

        # ----------------------------
        # DEALER FORCED PICK
        # ----------------------------
        dealer = self.dealer
        strat = self.strategies[dealer]
        is_forced_to_call_suit = (
            fixed_seat == 0 and force_suit_choice in remaining_suits
        )
        is_forced_alone_choice = fixed_seat == 0 and force_alone_choice is not None

        """suit, alone = strat.choose_trump(
            hand=self.hands[dealer],
            valid_suits=remaining_suits,
            force_call=True,
            force_suit_choice=force_suit_choice if fixed_seat == 0 else None,
            force_alone_choice=force_alone_choice if fixed_seat == 0 else None,
        )"""
        result = strat.choose_trump_stuck_dealer(
            hand=self.hands[dealer],
            turned_down_card=self.turned_down_card,
            valid_suits=(
                [force_suit_choice] if is_forced_to_call_suit else remaining_suits
            ),
        )

        # If forced to call trump here, force that result, keeping the strategy's loner logic
        # We still always need to run strat.choose_trump_stuck_dealer() to determine loner decision
        if is_forced_to_call_suit:
            # result[1] only works since we know they could only call alone on force_suit_choice
            # result can't be None
            result = (force_suit_choice, result[1])
            self.log(
                f"[CALL_TRUMP] {self.players[i]} was forced to call {SUITS[force_suit_choice]}"
            )

        # If going alone is forced to True/False, force that result
        if is_forced_alone_choice:
            result = (result[0], force_alone_choice)
            self.log(
                f"[CALL_TRUMP] {self.players[i]} was forced {'to go alone' if force_alone_choice else 'not to go alone'}"
            )

        suit, alone = result
        self.trump = suit
        self.maker = dealer
        self.makers = dealer % 2
        self.going_alone = alone
        self.loner = dealer
        self.sitting_out = (dealer + 2) % 4 if alone else None

        self.log(
            f"[CALL_TRUMP] Dealer {self.players[dealer]} forced to choose trump → {SUITS[suit]}"
            + (" AND GOES ALONE" if alone else "")
        )

        self.log(
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

                self.log(
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

            self.log(f"{self.players[p]} plays {card_name(card)}")

        led_suit = card_suit(trick[0])
        winner_offset = winner_of_trick(trick, self.trump, led_suit)
        winner = players_in_trick[winner_offset]

        self.log(f"{self.players[winner]} wins the trick\n")
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

    def score_hand(self, tricks_won, fixed_seat=None):
        makers = self.makers
        defenders = 1 - makers
        maker_tricks = tricks_won[makers]
        maker_points = 0
        fixed_team_points = 0
        loner_success = False

        # scoring logic
        if self.going_alone:
            if maker_tricks == 5:
                # Lone hand sweep
                maker_points = 4
                loner_success = True
                self.scores[makers] += 4
                self.log(
                    f"{self.players[self.loner]} wins ALL 5 tricks alone! +4 points"
                )
            elif maker_tricks >= 3:
                # Lone hand win (but not sweep)
                maker_points = 1
                self.scores[makers] += 1
                self.log(f"{self.players[self.loner]} wins the hand alone! +1 point")
            else:
                if self.two_player_hand:
                    # Lone defender win
                    maker_points = -4
                    self.scores[defenders] += 4
                    self.log(
                        f"{self.players[self.defender_loner]} DEFENDS ALONE successfully! +4 points"
                    )
                else:
                    # Lone hand euchred
                    maker_points = -2
                    self.scores[defenders] += 2
                    self.log(
                        f"{self.players[self.loner]} was euchred while going alone! Defenders +2"
                    )
        else:
            # Normal (non-loner) scoring
            if maker_tricks < 3:
                maker_points = -2
                self.scores[defenders] += 2
                self.log(f"Team {defenders} euchred the makers! +2")
            elif maker_tricks == 5:
                maker_points = 2
                self.scores[makers] += 2
                self.log(f"Team {makers} sweeps! +2")
            else:
                maker_points = 1
                self.scores[makers] += 1
                self.log(f"Team {makers} wins the hand! +1")

        self.log(f"Score: Team 0 = {self.scores[0]}, Team 1 = {self.scores[1]}\n")

        defender_points = -1 * maker_points
        fixed_team = fixed_seat % 2 if fixed_seat is not None else None
        if fixed_team is not None:
            fixed_seat_is_maker = fixed_seat == self.maker
            fixed_team_is_maker = fixed_team == makers
            if fixed_team_is_maker:
                fixed_team_points = maker_points
                fixed_team_tricks = maker_tricks
            else:
                fixed_team_points = defender_points
                fixed_team_tricks = tricks_won[defenders]
        else:
            # If not specified, set everything to 0/False
            fixed_seat_is_maker = False
            fixed_team_is_maker = False
            fixed_team_tricks = 0
            fixed_team_points = 0
            fixed_team_is_win = False
        fixed_team_is_win = fixed_team_points > 0

        return {
            "call_round": self.call_round,
            "is_maker": fixed_seat_is_maker,
            "is_maker_team": fixed_team_is_maker,
            "tricks": fixed_team_tricks,
            "points": fixed_team_points,
            "is_win": fixed_team_is_win,
        }

    # ------------------------------------------------------------
    # PLAY ONE HAND (5 TRICKS)
    # ------------------------------------------------------------
    def play_hand(
        self,
        is_fixed=False,
        fixed_hand=None,
        fixed_upcard=None,
        fixed_seat=None,
        force_suit_choice=None,
        force_alone_choice=None,
        rng=None,
    ):
        # Adjust fixed_seat relative to the dealer
        if fixed_seat is not None:
            relative_fixed_seat = (fixed_seat + self.dealer) % 4
        else:
            relative_fixed_seat = None

        if is_fixed:
            self.deal_fixed_hand(fixed_hand, fixed_upcard, relative_fixed_seat, rng)
        else:
            self.shuffle_and_deal()
        self.call_trump(relative_fixed_seat, force_suit_choice, force_alone_choice)
        self.check_defend_alone()

        self.log(f"Trump is {SUITS[self.trump]}")

        lead_player = self.first_active_player(self.dealer)
        tricks_won = [0, 0]  # team 0, team 1

        for _ in range(HAND_SIZE):
            winner = self.play_trick(lead_player)

            team = winner % 2
            tricks_won[team] += 1
            lead_player = winner

        outcome = self.score_hand(tricks_won, relative_fixed_seat)
        return outcome

    # ------------------------------------------------------------
    # FULL GAME LOOP
    # ------------------------------------------------------------
    def play_game(self, winning_score=10):
        while self.scores[0] < winning_score and self.scores[1] < winning_score:
            self.log(f"Dealer is {self.players[self.dealer]}")
            self.play_hand()
            # self.play_hand(True, [0, 1, 2, 3, 4], 5, 0, None, None, random.Random(42))
            self.dealer = (self.dealer + 1) % NUM_PLAYERS

        winner = 0 if self.scores[0] >= winning_score else 1
        self.log(f"*** Team {winner} wins the game! ***")


# ------------------------------------------------------------
# STANDALONE TEST
# ------------------------------------------------------------
if __name__ == "__main__":
    verbose = True
    if verbose:
        print("Starting Euchre test game...\n")

    strategies = [SimpleStrategy() for _ in range(4)]
    game = EuchreGame(
        players=["North", "East", "South", "West"],
        strategies=strategies,
        verbose=verbose,
    )
    game.play_game(winning_score=10)

    if verbose:
        print("\nFinal Score:")
        print(f"Team 0: {game.scores[0]}")
        print(f"Team 1: {game.scores[1]}")
        print("Game complete.")
