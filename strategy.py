from abc import ABC, abstractmethod
from cards import LEFT_BOWER_SUIT, card_rank, card_suit, effective_rank


# Abstract Base Class for all strategies
class Strategy(ABC):
    """
    A base class that all strategy classes must inherit from.
    Defines the required methods each strategy must implement.
    """

    @abstractmethod
    def play_card(self, hand, legal, trick, trump):
        """
        hand: full hand list
        legal: list returned from rules.legal_moves()
        trick: cards played so far (indexed by player seat)
        trump: trump suit int
        """
        pass

    @abstractmethod
    def choose_trump_first_round(
        self,
        hand,
        upcard,
        is_dealer=False,
        valid_suits=None,
    ):
        """
        Decide whether to call trump in the first round of calling trump.

        Parameters:
            hand: list of cards
            upcard: card int for upcard
            is_dealer: bool
            valid_suits: list of suit ints allowed, default None = all suits
        Returns:
            suit int 0-3 or None to pass
            None                  -> pass
            (suit, False)         -> call trump, not alone
            (suit, True)          -> call trump and go alone
        """
        pass

    @abstractmethod
    def choose_trump_second_round(
        self,
        hand,
        turned_down_card=None,
        valid_suits=None,
    ):
        """
        Decide whether to call trump in the first round of calling trump.

        Parameters:
            hand: list of cards
            turned_down_card: card int for turned down card
            valid_suits: list of suit ints allowed, default None = all suits
        Returns:
            suit int 0-3 or None to pass
            None                  -> pass
            (suit, False)         -> call trump, not alone
            (suit, True)          -> call trump and go alone
        """
        pass

    @abstractmethod
    def choose_trump_stuck_dealer(self, hand, turned_down_card, valid_suits=None):
        """
        Decide whether to call trump in the first round of calling trump.

        Parameters:
            hand: list of cards
            turned_down_card: card int for turned down card
            valid_suits: list of suit ints allowed, default None = all suits
        Returns:
            suit int 0-3 or None to pass
            None                  -> pass
            (suit, False)         -> call trump, not alone
            (suit, True)          -> call trump and go alone
        """
        pass

    @abstractmethod
    def discard(self, hand, trump_suit):
        """
        Choose a card to discard after picking up the upcard.
        Default: discard lowest non-trump, else lowest trump.
        """
        pass

    @abstractmethod
    def defend_alone(self, hand, trump_suit):
        """
        Decide whether to defend alone.
        Return True to defend alone, False otherwise.
        """
        pass

    @staticmethod
    def _play_weakest_legal_card(legal, trump):
        """
        Plays the weakest legal card available.
        """
        # If we are following suit, pick the weakest legal card
        # Strength is based on effective_rank for fast comparison.
        return min(legal, key=lambda c: effective_rank(c, trump))

    @staticmethod
    def _discard_lowest_non_trump(hand, trump_suit):
        """
        Discard the lowest non-trump card or the lowest trump card if no non-trumps are available.
        """
        non_trumps = [c for c in hand if card_suit(c) != trump_suit]
        if non_trumps:
            return min(non_trumps)
        return min(hand)

    def __repr__(self):
        """
        Optional toString or debug functionality.
        """
        return f"{self.__class__.__name__} Strategy"


class SimpleStrategy(Strategy):
    """
    A very fast, minimal strategy that allows the code to run.
    """

    def play_card(self, hand, legal, trick, trump):
        return self._play_weakest_legal_card(legal, trump)

    def __choose_trump(
        self,
        hand,
        upcard,
        is_dealer=False,
        valid_suits=None,
        call_threshold=5,
        call_threshold_dealer=4,
        loner_threshold=7,
        loner_bower_count_threshold=1,
    ):
        if valid_suits is None:
            valid_suits = [0, 1, 2, 3]

        suit_scores, bower_count = self.__calculate_hand_strength(
            hand, upcard, is_dealer, valid_suits
        )

        # ---- DETERMINE SUIT ----
        best_suit = max(valid_suits, key=lambda s: suit_scores[s])

        best_score = suit_scores[best_suit]

        threshold = call_threshold if not is_dealer else call_threshold_dealer
        if best_score < threshold:
            return None

        # ---- DETERMINE ALONE ----
        alone = (
            suit_scores[best_suit] >= loner_threshold
            and bower_count[best_suit] >= loner_bower_count_threshold
        )

        return best_suit, alone

    def choose_trump_first_round(self, hand, upcard, is_dealer=False, valid_suits=None):
        return self.__choose_trump(hand, upcard, is_dealer, valid_suits, 5, 4, 7, 1)

    def choose_trump_second_round(self, hand, turned_down_card, valid_suits=None):
        # Assume same logic as in first round, just with no upcard and different valid_suits
        # Will never be the dealer, since this is only called for the other 3 players
        return self.choose_trump_first_round(hand, None, False, valid_suits)

    def choose_trump_stuck_dealer(self, hand, turned_down_card, valid_suits=None):
        # Assume same logic as in first round, just with no upcard and different valid_suits
        # Will never be the dealer, since this is only called for the other 3 players
        return self.__choose_trump(hand, None, True, valid_suits, -1, -1, 7, 1)

    def discard(self, hand, trump_suit):
        return self._discard_lowest_non_trump(hand, trump_suit)

    def defend_alone(self, hand, trump_suit):
        strength = 0

        for c in hand:
            s = card_suit(c)
            r = card_rank(c)

            # Right bower
            if r == 2 and s == trump_suit:
                strength += 4

            # Left bower
            elif r == 2 and s == LEFT_BOWER_SUIT[trump_suit]:
                strength += 3

            # Trump A / K
            elif s == trump_suit and r >= 4:
                strength += 2

        # Conservative threshold (defending alone is rare)
        return strength >= 7  # set to 0 for testing defend alone logic

    def __calculate_hand_strength(self, hand, upcard, is_dealer, valid_suits):
        suit_scores = [0, 0, 0, 0]
        bower_count = [0, 0, 0, 0]

        for c in hand:
            s = card_suit(c)
            r = card_rank(c)

            if s not in valid_suits:
                continue

            if r == 2 and s == card_suit(c):  # Right bower
                suit_scores[s] += 4
                bower_count[s] += 1
            elif r == 2 and s == LEFT_BOWER_SUIT[s]:  # Left bower
                suit_scores[s] += 3
                bower_count[s] += 1
            elif r == 5:  # Ace
                suit_scores[s] += 2
            elif r in (4, 3):  # King / Queen
                suit_scores[s] += 1

        if upcard is not None and card_suit(upcard) in valid_suits:
            suit_scores[card_suit(upcard)] += 2 if is_dealer else 1

        return suit_scores, bower_count


class PassiveStrategy(Strategy):
    """Always chooses the most passive option possible. Useful for debugging by forcing 3 players to always pass."""

    def play_card(self, hand, legal, trick, trump):
        return self._play_weakest_legal_card(legal, trump)

    def choose_trump_first_round(self, hand, upcard, is_dealer=False, valid_suits=None):
        return None

    def choose_trump_second_round(self, hand, turned_down_card, valid_suits=None):
        return None

    def choose_trump_stuck_dealer(self, hand, turned_down_card, valid_suits=None):
        if valid_suits is None:
            valid_suits = [0, 1, 2, 3]
        suit_scores = self.__calculate_hand_strength(hand, valid_suits)
        best_suit = max(valid_suits, key=lambda s: suit_scores[s])
        return best_suit, False

    def discard(self, hand, trump_suit):
        return self._discard_lowest_non_trump(hand, trump_suit)

    def defend_alone(self, hand, trump_suit):
        return False

    def __calculate_hand_strength(self, hand, valid_suits):
        suit_scores = [0, 0, 0, 0]

        for c in hand:
            s = card_suit(c)
            r = card_rank(c)

            if s not in valid_suits:
                continue

            if r == 2 and s == card_suit(c):  # Right bower
                suit_scores[s] += 4
            elif r == 2 and s == LEFT_BOWER_SUIT[s]:  # Left bower
                suit_scores[s] += 3
            elif r == 5:  # Ace
                suit_scores[s] += 2
            elif r in (4, 3):  # King / Queen
                suit_scores[s] += 1

        return suit_scores
