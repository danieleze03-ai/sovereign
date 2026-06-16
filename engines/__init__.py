from config import PAIRS

class PairSelector:
    """
    At any moment, only one pair trades at a time.
    Selects the pair with the strongest setup.
    Priority: CRASH_500 > BOOM_500 > CRASH_1000 > BOOM_1000
    """
    PRIORITY = ["CRASH_500", "BOOM_500", "CRASH_1000", "BOOM_1000"]

    def select(self, evaluations: dict):
        """
        evaluations = {pair: {"should_enter": bool, "score": int}}
        Returns best pair or None.
        """
        best = None
        best_score = 0

        for pair in self.PRIORITY:
            if pair not in evaluations:
                continue
            ev = evaluations[pair]
            if ev.get("should_enter") and ev.get("score", 0) > best_score:
                best_score = ev["score"]
                best = pair

        return best