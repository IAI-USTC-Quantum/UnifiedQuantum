import uniqc.simulator as qsim
from uniqc.test._utils import uniq_test


def iswap_test():
    sim = qsim.StatevectorSimulator()
    sim.init_n_qubit(3)
    sim.sx(1)
    sim.xy(0, 1)

    print(sim.state)


@uniq_test("Test General")
def run_test_general():
    pass


if __name__ == "__main__":
    iswap_test()
