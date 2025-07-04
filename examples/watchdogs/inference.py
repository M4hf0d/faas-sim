from sim import docker
from sim.core import Environment
from sim.faas import (
    HTTPWatchdog,
    FunctionReplica,
    FunctionRequest,
    simulate_data_download,
)


class InferenceFunctionSim(HTTPWatchdog):
    """
    Inference model downloads and caches model at the beginning and  claims resources for HTTP server.
    During execution only inference happens.
    """

    def deploy(self, env: Environment, replica: FunctionReplica):
        # simulate a docker pull command for deploying the function (also done by sim.faassim.DockerDeploySimMixin)
        yield from docker.pull(env, replica.container.image, replica.node.ether_node)

    def setup(self, env: Environment, replica: FunctionReplica):
        super().setup(env, replica)
        # basic cpu usage, in %
        env.resource_state.put_resource(replica, "cpu", 0.08)

        # basic memory consumption, in MB
        env.resource_state.put_resource(replica, "memory", 200)

        yield from simulate_data_download(env, replica)

    def teardown(self, env: Environment, replica: FunctionReplica):
        # basic cpu usage, in %
        env.resource_state.remove_resource(replica, "cpu", 0.08)

        # basic memory consumption, in MB
        env.resource_state.remove_resource(replica, "memory", 200)
        yield env.timeout(0)

    def claim_resources(
        self, env: Environment, replica: FunctionReplica, request: FunctionRequest
    ):
        # no setup time, no memory because everything is cached - only cpu usage
        env.resource_state.put_resource(replica, "cpu", 0.2)
        yield env.timeout(0)

    def release_resources(
        self, env: Environment, replica: FunctionReplica, request: FunctionRequest
    ):
        env.resource_state.remove_resource(replica, "cpu", 0.2)
        yield env.timeout(0)

    def execute(
        self, env: Environment, replica: FunctionReplica, request: FunctionRequest
    ):
        yield env.timeout(0.2)
