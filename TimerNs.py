import time
class TimerNs(object):
    def __init__(self, name=None):
        self.name = name

        self.default_message = 'Timer'

        # beginning of epoch by default
        self.start()
        self.elapsed_ns = None

    def calculate_elapsed(self):
        self.elapsed_ns = self.tend - self.tstart
        self.elapsed = round((self.tend - self.tstart)/(10**9)) # seconds

    def start(self):
        self.tstart = time.time_ns()

    def end(self):
        self.tend = time.time_ns()
        self.calculate_elapsed()

    def __enter__(self):
        self.start()

    def __exit__(self, type, value, traceback):
        self.end()

        if self.name:
            print('[%s] ' % self.name, end="")

        print('Elapsed: %s' % (self.elapsed_ns))

    def tic(self,  message=None, return_value=False) -> int:
        """ sets initial timestamp """
        self.start()

        message = message or self.message or self.default_message

        if return_value:
            return self.tstart

        print(self.tstart)

    def toc(self, message=None, return_value=False) -> None:
        """ sets self.tend ti current """
        self.end()
        self.tstart = self.tend

        message = message or self.message or self.default_message
        if message:
            self.message = message

        if return_value:
            return self.elapsed_ns

        print(f'[{self.message}] Elapsed {self.elapsed}s')