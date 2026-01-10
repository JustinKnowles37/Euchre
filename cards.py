import random

# ---------- CONSTANTS ----------

SUITS = ["Clubs", "Diamonds", "Hearts", "Spades"]
RANKS = ["9", "T", "J", "Q", "K", "A"]

# Precompute lookup tables for speed
CARD_TO_SUIT = [i // 6 for i in range(24)]
CARD_TO_RANK = [i % 6 for i in range(24)]
CARD_NAME = [f"{RANKS[r]} of {SUITS[s]}" for s in range(4) for r in range(6)]
CARD_COLOR = [0, 1, 1, 0]  # Clubs/Spades black=0, Diamonds/Hearts red=1

# Left-bower mapping (same color suit)
# Clubs ↔ Spades, Diamonds ↔ Hearts
LEFT_BOWER_SUIT = [3, 2, 1, 0]


# ---------- CARD HELPERS ----------


def card_suit(card):
    return CARD_TO_SUIT[card]


def card_rank(card):
    return CARD_TO_RANK[card]


def card_name(card):
    return CARD_NAME[card]


def card_int(card_input):
    """
    Convert a card identifier (e.g., "9h", "Js") into an integer card ID.
    If a list of card identifiers is passed, return a list of corresponding integer card IDs.
    Assumes a specific mapping for card strings to integers.
    """
    card_map = {
        "9C": 0,
        "TC": 1,
        "JC": 2,
        "QC": 3,
        "KC": 4,
        "AC": 5,
        "9D": 6,
        "TD": 7,
        "JD": 8,
        "QD": 9,
        "KD": 10,
        "AD": 11,
        "9H": 12,
        "TH": 13,
        "JH": 14,
        "QH": 15,
        "KH": 16,
        "AH": 17,
        "9S": 18,
        "TS": 19,
        "JS": 20,
        "QS": 21,
        "KS": 22,
        "AS": 23,
    }

    if isinstance(card_input, int):
        return card_input

    elif isinstance(card_input, str):
        return card_map[card_input.strip().upper()]

    elif isinstance(card_input, list):
        return [
            card_map[card.strip().upper()] if isinstance(card, str) else card
            for card in card_input
        ]

    else:
        raise TypeError(
            "Input must be a string, int, or a list of strings and/or ints."
        )


def suit_int(suit_name):
    """
    Converts a suit name (e.g., "Clubs") to its corresponding integer value.

    Parameters:
        suit_name (str or None): The name of the suit (case-insensitive) or None.

    Returns:
        int or None: The integer corresponding to the suit, or None if the input is None.

    Raises:
        ValueError: If the suit name is invalid (not in SUITS).
    """
    if suit_name is None:
        return None  # If the input is None, return None directly

    suit_name = suit_name.strip().capitalize()  # Normalize input
    if suit_name not in SUITS:
        raise ValueError(f"Invalid suit name: {suit_name}. Must be one of {SUITS}.")
    return SUITS.index(suit_name)


def is_right_bower(card, trump_suit):
    """
    Jack of trump suit.
    """
    return card_rank(card) == 2 and card_suit(card) == trump_suit


def is_left_bower(card, trump_suit):
    """
    Jack of the same-color suit as trump.
    """
    return card_rank(card) == 2 and card_suit(card) == LEFT_BOWER_SUIT[trump_suit]


def is_trump(card, trump_suit):
    """
    Normal trump + left bower.
    """
    return card_suit(card) == trump_suit or is_left_bower(card, trump_suit)


def effective_rank(card, trump_suit):
    """
    Returns integer representing rank strength for trick comparison.
    Higher = stronger.

    Trump hierarchy:
        Right bower (8)
        Left bower  (7)
        A (6), K (5), Q (4), J (3), T (2), 9 (1)

    Non-trump:
        A (5), K (4), Q (3), J (2), T (1), 9 (0)
    """
    r = card_rank(card)

    # Bowers override all
    if is_right_bower(card, trump_suit):
        return 8
    if is_left_bower(card, trump_suit):
        return 7

    if is_trump(card, trump_suit):
        # Normal trump ranks: 9→A → 1..6
        return 1 + r  # r = 0..5

    # Non-trump: 9→A → 0..5
    return r


# ---------- DECK CLASS ----------


class Deck:
    def __init__(self):
        self.cards = list(range(24))

    def shuffle(self, seed=None):
        if seed is not None:
            random.seed(seed)
        random.shuffle(self.cards)

    def deal(self):
        """
        Deals four 5-card hands + upcard (1 card remains).
        Returns:
            hands = [hand0, hand1, hand2, hand3], each a list of 5 card ints
            upcard = int
        """
        hands = [self.cards[i * 5 : (i + 1) * 5] for i in range(4)]
        upcard = self.cards[20]
        return hands, upcard


# ---------- TESTING ----------


def _test_card_logic():
    # Right bower test (e.g., Jack of Hearts if trump = Hearts)
    jack_hearts = 2 + 2 * 6  # suit=2 (Hearts), rank_index=2 (J)
    assert is_right_bower(jack_hearts, 2)

    # Left bower test (Jack of Diamonds if trump = Hearts)
    jack_diamonds = 2 + 1 * 6  # suit=1 (Diamonds), rank_index=2 (J)
    assert is_left_bower(jack_diamonds, 2)

    # Left bower behaves as trump
    assert is_trump(jack_diamonds, 2)

    # Effective ranks: right bower > left bower > A
    ace_hearts = 5 + 2 * 6  # A of hearts
    assert effective_rank(jack_hearts, 2) > effective_rank(jack_diamonds, 2)
    assert effective_rank(jack_diamonds, 2) > effective_rank(ace_hearts, 2)

    print("All tests passed.")


if __name__ == "__main__":
    _test_card_logic()
