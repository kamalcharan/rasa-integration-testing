from os import getpid
from socket import gethostname

TRACKER_ID_SIGNATURE = "ITEST"


def generate_tracker_id_from_scenario_name(
    run_timestamp: float, scenario_name: str
) -> str:
    # Build a unique identifier following a format similar to this:
    #
    #     "UTEST_woo20124_1569249227.5879638_ask_installation_basic_flows_success"
    #      --+-- ---+---- ---------+-------- -------+----------------------------
    #        |      |              |                +---- name of the script
    #        |      |              +--------------------- epoch of the test run
    #        |      |                                     execution time
    #        |      +------------------------------------ host of client + process id
    #        +------------------------------------------- unique signature
    unique_identifier = f"{gethostname()}{str(getpid())}_{run_timestamp}"
    return f"{TRACKER_ID_SIGNATURE}_{unique_identifier}_{scenario_name}"
