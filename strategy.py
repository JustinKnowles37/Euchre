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


# TODO - Have not reviewed this strategy code much.
# From a quick skim, lots of faulty logic, but it's still better than previous iterations
class Strategy2(Strategy):
    """
    An advanced strategy that uses more sophisticated logic for trump selection and card play.
    """

    def play_card(self, hand, legal, trick, trump):
        """
        Improved card play logic that considers:
        - Winning the trick vs throwing off weak cards
        - Protecting valuable cards
        - Context of the trick
        """
        if not legal:
            return None

        # If only one card is legal, play it
        if len(legal) == 1:
            return legal[0]

        # Count cards in trick so far
        cards_played = sum(1 for c in trick if c is not None)

        # If leading (no cards played yet), lead strategically
        if cards_played == 0:
            return self._choose_lead(hand, trump)

        # If following, decide whether to win or throw off
        trick_winner = self._current_trick_leader(trick, trump)
        can_win = any(
            effective_rank(card, trump) > effective_rank(trick[trick_winner], trump)
            and card_suit(card) == card_suit(trick[trick_winner])
            for card in legal
        )

        if can_win and self._should_win_trick(hand, legal, trick, trump):
            # Play the lowest card that wins
            winning_cards = [
                card
                for card in legal
                if effective_rank(card, trump)
                > effective_rank(trick[trick_winner], trump)
                and card_suit(card) == card_suit(trick[trick_winner])
            ]
            return min(winning_cards, key=lambda c: effective_rank(c, trump))
        else:
            # Throw off the weakest card
            return self._play_weakest_legal_card(legal, trump)

    def _choose_lead(self, hand, trump):
        """
        Choose a strong card to lead the trick.
        Prefer leading trump or high cards in suits.
        """
        trump_cards = [c for c in hand if card_suit(c) == trump]
        non_trump = [c for c in hand if card_suit(c) != trump]

        # If we have strong trumps, consider leading them
        strong_trumps = [c for c in trump_cards if card_rank(c) >= 4]
        if strong_trumps:
            return max(strong_trumps, key=lambda c: effective_rank(c, trump))

        # Otherwise, lead a strong non-trump card
        strong_non_trump = [c for c in non_trump if card_rank(c) >= 4]
        if strong_non_trump:
            return max(strong_non_trump, key=lambda c: card_rank(c))

        # Default to weakest card
        return min(hand, key=lambda c: effective_rank(c, trump))

    def _current_trick_leader(self, trick, trump):
        """
        Determine which player is currently winning the trick.
        """
        leader_idx = 0
        leader_card = trick[0]

        for i, card in enumerate(trick[1:], 1):
            if card is None:
                continue
            if self._card_beats(card, leader_card, trump):
                leader_idx = i
                leader_card = card

        return leader_idx

    def _card_beats(self, card1, card2, trump):
        """
        Check if card1 beats card2 in the given trump.
        """
        if card2 is None:
            return True

        suit1 = card_suit(card1)
        suit2 = card_suit(card2)

        # Different suits - only trump can win
        if suit1 != suit2:
            return suit1 == trump

        # Same suit - higher effective rank wins
        return effective_rank(card1, trump) > effective_rank(card2, trump)

    def _should_win_trick(self, hand, legal, trick, trump):
        """
        Heuristic to decide if we should try to win this trick.
        """
        # Count remaining high cards in our hand
        high_cards = sum(1 for c in hand if card_rank(c) >= 4)

        # If we have many high cards, be aggressive
        if high_cards >= 3:
            return True

        # If trick has high cards, be more conservative
        trick_rank = max((card_rank(c) for c in trick if c is not None), default=0)

        # Try to win tricks with low-to-medium value
        return trick_rank <= 3

    def choose_trump_first_round(self, hand, upcard, is_dealer=False, valid_suits=None):
        """
        Improved trump selection with better thresholds and hand analysis.
        """
        if valid_suits is None:
            valid_suits = [0, 1, 2, 3]

        suit_scores, trump_cards = self._score_hand_comprehensive(
            hand, upcard, valid_suits
        )

        # Use position-adjusted thresholds
        call_threshold = 5.5 if not is_dealer else 4.5
        loner_threshold = 7.5

        best_suit = max(valid_suits, key=lambda s: suit_scores[s])
        best_score = suit_scores[best_suit]

        # Don't call weak hands
        if best_score < call_threshold:
            return None

        # Decide if we should go alone
        alone = best_score >= loner_threshold and trump_cards[best_suit] >= 2

        return best_suit, alone

    def choose_trump_second_round(self, hand, turned_down_card, valid_suits=None):
        """
        Second round trump selection (higher bar since first was passed).
        """
        if valid_suits is None:
            valid_suits = [0, 1, 2, 3]

        suit_scores, trump_cards = self._score_hand_comprehensive(
            hand, None, valid_suits
        )

        # Higher threshold in second round
        call_threshold = 6.0

        best_suit = max(valid_suits, key=lambda s: suit_scores[s])
        best_score = suit_scores[best_suit]

        if best_score < call_threshold:
            return None

        # Go alone only with very strong hands
        alone = best_score >= 8.0 and trump_cards[best_suit] >= 2

        return best_suit, alone

    def choose_trump_stuck_dealer(self, hand, turned_down_card, valid_suits=None):
        """
        Dealer is stuck - must pick something. Choose best available.
        """
        if valid_suits is None:
            valid_suits = [0, 1, 2, 3]

        suit_scores, trump_cards = self._score_hand_comprehensive(
            hand, None, valid_suits
        )

        best_suit = max(valid_suits, key=lambda s: suit_scores[s])

        # Never go alone when stuck
        return best_suit, False

    def discard(self, hand, trump_suit):
        """
        Improved discard logic - discard based on hand context.
        """
        # Prefer discarding non-trump cards
        non_trumps = [c for c in hand if card_suit(c) != trump_suit]

        if non_trumps:
            # Among non-trump, discard lowest rank cards first
            return min(non_trumps, key=lambda c: card_rank(c))

        # If all trump, discard lowest trump
        return min(hand, key=lambda c: effective_rank(c, trump_suit))

    def defend_alone(self, hand, trump_suit):
        """
        Decide whether to defend alone against a lone maker.
        Only defend alone if hand is very strong.
        """
        suit_scores, _ = self._score_hand_comprehensive(hand, None, [trump_suit])

        # Only defend alone with exceptional trump strength
        return suit_scores[trump_suit] >= 8.0

    def _score_hand_comprehensive(self, hand, upcard, valid_suits):
        """
        Comprehensive hand evaluation considering card strength and distribution.
        Returns (suit_scores, trump_count_per_suit)
        """
        suit_scores = [0, 0, 0, 0]
        trump_cards = [0, 0, 0, 0]

        for card in hand:
            suit = card_suit(card)
            rank = card_rank(card)

            if suit not in valid_suits:
                continue

            # Score card based on rank
            if rank == 2:  # Jack (Right bower in trump)
                suit_scores[suit] += 5
                trump_cards[suit] += 1
            elif rank == 1:  # Jack from other red/black suit (Left bower)
                # Bowers are worth a lot
                left_bower_suit = LEFT_BOWER_SUIT[suit]
                if left_bower_suit in valid_suits:
                    suit_scores[left_bower_suit] += 4
                    trump_cards[left_bower_suit] += 1
            elif rank == 5:  # Ace
                suit_scores[suit] += 3
            elif rank == 4:  # King
                suit_scores[suit] += 2
            elif rank == 3:  # Queen
                suit_scores[suit] += 1
            elif rank == 0:  # 10
                suit_scores[suit] += 1.5

        # Bonus for upcard if available
        if upcard is not None and card_suit(upcard) in valid_suits:
            upcard_suit = card_suit(upcard)
            suit_scores[upcard_suit] += 2 if len(hand) > 1 else 1

        return suit_scores, trump_cards
