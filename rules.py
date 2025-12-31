from cards import (
    card_suit,
    is_trump,
    effective_rank,
)


# ------------------------------------------------------------
#  LEGAL MOVES
# ------------------------------------------------------------


def legal_moves(hand, led_card, trump_suit):
    """
    Returns the list of cards in 'hand' that can legally be played.

    Euchre rule: if you can follow the led suit, you must follow it.
    Special case: left bower counts as trump suit, not its printed suit.
    """
    if led_card is None:
        # Leader can play anything
        return hand[:]

    led_suit = card_suit(led_card)
    if is_trump(led_card, trump_suit):
        led_suit = trump_suit  # led card is trump (maybe left bower)

    # Cards that match the led suit (considering bower behavior)
    following = []
    for c in hand:
        c_suit = card_suit(c)
        if is_trump(c, trump_suit):
            c_suit = trump_suit
        if c_suit == led_suit:
            following.append(c)

    # If you can follow suit, you must
    if following:
        return following

    # Otherwise any card may be played
    return hand[:]


# ------------------------------------------------------------
#  TRICK WINNER LOGIC
# ------------------------------------------------------------


def winner_of_trick(trick_cards, trump_suit, led_suit):
    """
    trick_cards: list of 4 (3 if loner) card ints, ordered by play order
    led_suit: the suit (or trump_suit if trump was led)

    Returns: index 0..3 (0..2 if loner) of the winning card
    """
    best_index = 0
    best_card = trick_cards[0]
    best_trump = is_trump(best_card, trump_suit)
    best_rank = effective_rank(best_card, trump_suit)

    for i in range(1, len(trick_cards)):
        c = trick_cards[i]
        is_tr = is_trump(c, trump_suit)

        # Must compare within same suit group
        # If one is trump and the other isn't, trump wins
        if is_tr and not best_trump:
            best_index = i
            best_card = c
            best_trump = True
            best_rank = effective_rank(c, trump_suit)
            continue

        if is_tr == best_trump:
            # Same category: both trump or both non-trump
            # Must follow led suit unless trumping
            suit_c = card_suit(c)
            suit_best = card_suit(best_card)

            # Adjust for bower (left bower = trump suit)
            if is_tr:
                suit_c = trump_suit
                suit_best = trump_suit
            else:
                # Non-trump following led suit
                if suit_c != led_suit and suit_best == led_suit:
                    continue
                if suit_best != led_suit and suit_c == led_suit:
                    best_index = i
                    best_card = c
                    best_rank = effective_rank(c, trump_suit)
                    continue

            # Same suit competition
            r = effective_rank(c, trump_suit)
            if r > best_rank:
                best_index = i
                best_card = c
                best_rank = r

    return best_index


# ------------------------------------------------------------
#  PLAY A SINGLE TRICK
# ------------------------------------------------------------


def play_trick(hands, leader_index, trump_suit, strategies, sitting_out=None):
    """
    Plays one trick.

    Parameters:
        hands: list of 4 lists of cards
        leader_index: player index 0..3
        trump_suit: 0-3
        strategies: list of objects with method play_card()
        sitting_out: player index who does not play (None if no loner)

    Returns:
        winner (0..3), trick_cards (list of cards played in order)
    """
    trick_cards = []  # cards in play order
    trick_players = []  # corresponding player indices
    led_card = None

    for offset in range(4):
        p = (leader_index + offset) % 4

        # Skip the partner if someone is going alone
        if sitting_out is not None and p == sitting_out:
            continue

        hand = hands[p]

        lm = legal_moves(hand, led_card, trump_suit)
        chosen = strategies[p].play_card(hand, lm, trick_cards, trump_suit)

        trick_cards.append(chosen)
        trick_players.append(p)
        hand.remove(chosen)

        if led_card is None:
            led_card = chosen

    # Determine led suit (accounting for trump)
    led_suit = card_suit(led_card)
    if is_trump(led_card, trump_suit):
        led_suit = trump_suit

    # winner_of_trick now works for 3 or 4 cards
    winner_offset = winner_of_trick(
        trick_cards,
        trump_suit=trump_suit,
        led_suit=led_suit,
    )

    winner = trick_players[winner_offset]
    return winner, trick_cards


# ------------------------------------------------------------
#  BASIC INTERNAL TESTS
# ------------------------------------------------------------


def _test_rules():
    # Simple mock "strategy" that plays the first legal card
    class FirstLegal:
        def play_card(self, hand, legal, trick, trump):
            return legal[0]

    s = [FirstLegal() for _ in range(4)]

    # Cards (computed as suit*6 + rank_idx):
    # 0 = 9 of Clubs
    # 7 = 10 of Diamonds
    # 2 = J of Clubs
    # 9 = Q of Diamonds  <-- this is the trump Q we want to test

    hands = [
        [0],  # Player 0: 9 of Clubs (leads)
        [7],  # Player 1: 10 of Diamonds (trump)
        [2],  # Player 2: J of Clubs
        [9],  # Player 3: Q of Diamonds (trump, should win)
    ]

    leader = 0
    trump = 1  # Diamonds

    winner, trick = play_trick(hands, leader, trump, s)

    # With diamonds trump, player 3's Q of Diamonds should beat player 1's 10 of Diamonds
    assert winner == 3, f"expected winner 3 (Diamonds Q), got {winner}"

    print("rules.py internal tests passed.")


if __name__ == "__main__":
    _test_rules()
