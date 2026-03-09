import time

class Timer:
    elapsed : int 
    def __enter__(self):
        self.start = time.perf_counter()
        return self
    def __exit__(self, *exc):
        self.elapsed = (time.perf_counter() - self.start) * 1000
