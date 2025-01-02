import os
import signal
import time


class DVMFramework:
    dvms = []

    def __init__(self):
        self.dvms = []


    def add(self, dvm):
        self.dvms.append(dvm)

    def run(self):
        for dvm in self.dvms:
            dvm.run()

        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            for dvm in self.dvms:
                dvm.join()
        print("All DVMs shut down.")
        os.kill(os.getpid(), signal.SIGKILL)
        exit(1)

