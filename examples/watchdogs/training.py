import logging

from sim import docker
from sim.core import Environment
from sim.faas import ForkingWatchdog, FunctionReplica, FunctionRequest

logger = logging.getLogger(__name__)


class TrainingFunctionSim(ForkingWatchdog):
    """
    Training forks per request
    Claims resources per request and downloads per request the model
    """

    def deploy(self, env: Environment, replica: FunctionReplica):
        # simulate a docker pull command for deploying the function (also done by sim.faassim.DockerDeploySimMixin)
        yield from docker.pull(env, replica.container.image, replica.node.ether_node)

    def startup(self, env: Environment, replica: FunctionReplica):
        logger.info(
            "[simtime=%.2f] starting up function replica for function %s",
            env.now,
            replica.function.name,
        )

        # you could create a very fine-grained setup routines here
        yield env.timeout(1)  # simulate docker startup

    def claim_resources(
        self, env: Environment, replica: FunctionReplica, request: FunctionRequest
    ):
        env.resource_state.put_resource(replica, "cpu", 0.7)
        env.resource_state.put_resource(replica, "memory", 0.3)
        yield env.timeout(0)

    def release_resources(
        self, env: Environment, replica: FunctionReplica, request: FunctionRequest
    ):
        env.resource_state.remove_resource(replica, "cpu", 0.2)
        yield env.timeout(0)

    def execute(
        self, env: Environment, replica: FunctionReplica, request: FunctionRequest
    ):
        # mock download, for actual network download simulation look at simulate_data_download
        yield env.timeout(1)

        # training
        yield env.timeout(5)

        # mock upload
        yield env.timeout(1)

    def teardown(self, env: Environment, replica: FunctionReplica):
        yield env.timeout(0)
