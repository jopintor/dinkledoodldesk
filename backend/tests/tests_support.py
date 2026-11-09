"""Small test doubles shared by several test modules."""


class FakeClock:
    """Monotonic and wall clock in one; `sleep` advances time instead of waiting."""

    def __init__(self, start: float = 1_000_000.0) -> None:
        self.t = start
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds
