class Hand:
    def __init__(self):
        self.cards = []

    def add(self, card):
        self.cards.append(card)

    def value(self):
        total = 0
        aces = 0
        for c in self.cards:
            if c.rank == "A":
                aces += 1
                total += 11
            elif c.rank in ("J", "Q", "K"):
                total += 10
            else:
                total += int(c.rank)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    def is_bust(self):
        return self.value() > 21

    def is_blackjack(self):
        return len(self.cards) == 2 and self.value() == 21

    def is_soft(self):
        """True when an ace is still counted as 11."""
        if not any(c.rank == "A" for c in self.cards):
            return False
        hard_total = 0
        for c in self.cards:
            if c.rank == "A":
                hard_total += 1
            elif c.rank in ("J", "Q", "K"):
                hard_total += 10
            else:
                hard_total += int(c.rank)
        return self.value() > hard_total
