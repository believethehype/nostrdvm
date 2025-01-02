import os
import signal
import time
from nostr_dvm.utils.print_utils import bcolors


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
                if dvm.dvm_config.NIP89 is not None:
                    print(bcolors.CYAN + "Shuting down " + dvm.dvm_config.NIP89.NAME  + bcolors.ENDC)
                dvm.join()
        print(bcolors.GREEN +"All DVMs shut down." + bcolors.ENDC)
        os.kill(os.getpid(), signal.SIGKILL)
        exit(1)

    def get_dvms(self):
        return self.dvms

