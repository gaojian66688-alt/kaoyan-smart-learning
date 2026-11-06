import math
from datetime import datetime, timedelta
from app.config import settings

# FSRS standard constants
DECAY = -0.5
FACTOR = 19.0 / 81.0  # (0.9 ** (1 / DECAY) - 1)

class FSRSScheduler:
    """
    Free Spaced Repetition Scheduler (FSRS v4.5 compatible).
    Ratings:
      1: Again (忘记)
      2: Hard (困难)
      3: Good (记得)
      4: Easy (轻松)
    """

    def __init__(self, w: list[float] = None, request_retention: float = None):
        self.w = w if w is not None else settings.FSRS_W
        self.request_retention = request_retention if request_retention is not None else settings.FSRS_REQUEST_RETENTION

    def retrievability(self, elapsed_days: float, stability: float) -> float:
        if stability <= 0:
            return 0.0
        return (1.0 + FACTOR * (elapsed_days / stability)) ** DECAY

    def next_interval(self, stability: float) -> float:
        if stability <= 0:
            return 1.0
        interval = (stability / FACTOR) * (self.request_retention ** (1.0 / DECAY) - 1.0)
        return max(1.0, min(float(settings.FSRS_MAXIMUM_INTERVAL), round(interval, 2)))

    def init_difficulty(self, rating: int) -> float:
        # D0(G) = w4 - (G - 3) * w5
        d = self.w[4] - (rating - 3) * self.w[5]
        return max(1.0, min(10.0, d))

    def next_difficulty(self, d: float, rating: int) -> float:
        # Mean reversion: w7 * D0(3) + (1 - w7) * (D - w6 * (G - 3))
        d0_3 = self.init_difficulty(3)
        next_d = self.w[7] * d0_3 + (1.0 - self.w[7]) * (d - self.w[6] * (rating - 3))
        return max(1.0, min(10.0, next_d))

    def init_stability(self, rating: int) -> float:
        # S0(G) = w[G-1]
        idx = max(0, min(3, rating - 1))
        return max(0.1, self.w[idx])

    def next_recall_stability(self, d: float, s: float, r: float, rating: int) -> float:
        hard_penalty = self.w[15] if rating == 2 else 1.0
        easy_bonus = self.w[16] if rating == 4 else 1.0
        # S'_r = S * (1 + exp(w8) * (11 - D) * S^(-w9) * (exp((1 - R) * w10) - 1) * bonus)
        inc = (
            math.exp(self.w[8])
            * (11.0 - d)
            * (s ** (-self.w[9]))
            * (math.exp((1.0 - r) * self.w[10]) - 1.0)
            * hard_penalty
            * easy_bonus
        )
        return max(0.1, s * (1.0 + inc))

    def next_forget_stability(self, d: float, s: float, r: float) -> float:
        # S'_f = w11 * D^(-w12) * ((S + 1)^w13 - 1) * exp((1 - R) * w14)
        s_inc = (
            self.w[11]
            * (d ** (-self.w[12]))
            * (((s + 1.0) ** self.w[13]) - 1.0)
            * math.exp((1.0 - r) * self.w[14])
        )
        return max(0.1, min(s, s_inc))

    def review(
        self,
        rating: int,
        last_stability: float = 0.0,
        last_difficulty: float = 0.0,
        last_review_date: datetime = None,
        now: datetime = None
    ) -> dict:
        """
        Executes a review step and calculates new state:
        returns: {
            'stability': float,
            'difficulty': float,
            'interval_days': float,
            'due_date': datetime,
            'state': int
        }
        """
        if now is None:
            now = datetime.utcnow()

        if last_review_date is None or last_stability <= 0:
            # First time review
            new_s = self.init_stability(rating)
            new_d = self.init_difficulty(rating)
            new_state = 1 if rating < 3 else 2
        else:
            elapsed_days = max(0.0, (now - last_review_date).total_seconds() / 86400.0)
            r = self.retrievability(elapsed_days, last_stability)
            new_d = self.next_difficulty(last_difficulty, rating)

            if rating == 1:
                new_s = self.next_forget_stability(new_d, last_stability, r)
                new_state = 3  # Relearning
            else:
                new_s = self.next_recall_stability(new_d, last_stability, r, rating)
                new_state = 2  # Review

        interval_days = self.next_interval(new_s)
        due_date = now + timedelta(days=interval_days)

        return {
            "stability": round(new_s, 4),
            "difficulty": round(new_d, 4),
            "interval_days": round(interval_days, 2),
            "due_date": due_date,
            "state": new_state,
        }

default_fsrs = FSRSScheduler()
