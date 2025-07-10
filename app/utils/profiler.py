import time

class Profiler:
    def __init__(self):
        self.start = time.time()
        self.marks = []

    def mark(self, label: str):
        now = time.time()
        elapsed = now - self.start
        self.marks.append((label, elapsed))
        print(f"⏱️ {label}: {elapsed:.2f}s")

    def summary(self):
        print("\n=== Timing Summary ===")
        for label, elapsed in self.marks:
            print(f"{label:<30} {elapsed:.2f}s")
        print("======================\n")
