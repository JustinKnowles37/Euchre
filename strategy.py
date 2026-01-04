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
    def choose_trump(
        self, hand, upcard=None, is_dealer=False, valid_suits=None, force=False
    ):
        """
        Decide whether to call trump.

        Parameters:
            hand: list of cards
            upcard: card int (optional) for first round
            is_dealer: bool
            valid_suits: list of suit ints allowed (for 2nd round), default None = all suits
            force: bool, if True must pick a suit
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
        # If we are following suit, pick the weakest legal card
        # Strength is based on effective_rank for fast comparison.
        return min(legal, key=lambda c: effective_rank(c, trump))

    # Optional helpers used during bidding
    def choose_trump(
        self, hand, upcard=None, is_dealer=False, valid_suits=None, force=False
    ):
        if valid_suits is None:
            valid_suits = [0, 1, 2, 3]

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

        best_suit = max(valid_suits, key=lambda s: suit_scores[s])
        best_score = suit_scores[best_suit]

        # Lower these thresholds for testing loner logic
        threshold = 5 if not is_dealer else 4
        if not force and best_score < threshold:
            return None

        # ---- GOING ALONE LOGIC ----
        alone = suit_scores[best_suit] >= 7 and bower_count[best_suit] >= 1

        return (best_suit, alone)

    def discard(self, hand, trump_suit):
        non_trumps = [c for c in hand if card_suit(c) != trump_suit]
        if non_trumps:
            return min(non_trumps)
        return min(hand)

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
