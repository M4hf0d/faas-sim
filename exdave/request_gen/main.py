import logging
from typing import List

import ether.scenarios.urbansensing as scenario
from sim.requestgen import expovariate_arrival_profile, constant_rps_profile
from skippy.core.utils import parse_size_string

from sim import docker
from sim.benchmark import Benchmark
from sim.context.platform.deployment.model import (
    SimFunctionDeployment,
    SimScalingConfiguration,
)
from sim.core import Environment
from sim.docker import ImageProperties
from sim.faas.core import SimResourceConfiguration
from sim.faassim import Simulation
from sim.requestgen import SimpleFunctionRequestFactory, function_trigger
from sim.topology import Topology

logger = logging.getLogger(__name__)

from faas.system.core import (
    FunctionContainer,
    Function,
    FunctionImage,
    DeploymentRanking,
)
from sim.faas import FunctionRequest


def main():
    logging.basicConfig(level=logging.DEBUG)

    # a topology holds the cluster configuration and network topology
    topology = example_topology()

    # a benchmark is a simpy process that sets up the runtime system (e.g., creates container images, deploys functions)
    # and creates workload by simulating function requests
    benchmark = ExampleBenchmark()

    # a simulation runs until the benchmark process terminates
    sim = Simulation(topology, benchmark)
    sim.run()


def example_topology() -> Topology:
    t = Topology()
    scenario.UrbanSensingScenario().materialize(t)
    t.init_docker_registry()

    return t


class ExampleBenchmark(Benchmark):

    def __init__(self, request_factory: SimpleFunctionRequestFactory = None):
        self.request_factory = request_factory
        if self.request_factory is None:
            self.request_factory = SimpleFunctionRequestFactory()

    def setup(self, env: Environment):
        containers: docker.ContainerRegistry = env.container_registry

        # populate the global container registry with images
        containers.put(
            ImageProperties("python-pi-cpu", parse_size_string("58M"), arch="arm32")
        )
        containers.put(
            ImageProperties("python-pi-cpu", parse_size_string("58M"), arch="x86")
        )
        containers.put(
            ImageProperties("python-pi-cpu", parse_size_string("58M"), arch="aarch64")
        )

        # log all the images in the container
        for name, tag_dict in containers.images.items():
            for tag, images in tag_dict.items():
                logger.info("%s, %s, %s", name, tag, images)

    def run(self, env: Environment):
        # deploy functions
        deployments = self.prepare_deployments()

        for deployment in deployments:
            yield from env.faas.deploy(deployment)

        # block until replicas become available (scheduling has finished and replicas have been deployed on the node)
        logger.info("waiting for replica")
        yield env.process(env.faas.poll_available_replica("python-pi"))

        # generate profile
        ia_generator = expovariate_arrival_profile(constant_rps_profile(rps=20))

        # run profile
        yield from function_trigger(
            env, deployments[0], self.request_factory, ia_generator, max_requests=100
        )

    def prepare_deployments(self) -> List[SimFunctionDeployment]:
        python_pi_fd = self.prepare_python_pi_deployment()

        return [python_pi_fd]

    def prepare_python_pi_deployment(self):
        # Design Time

        python_pi = "python-pi"
        python_pi_cpu = FunctionImage(image="python-pi-cpu")
        python_pi_fn = Function(python_pi, fn_images=[python_pi_cpu])

        # Run time

        python_pi_fn_container = FunctionContainer(
            python_pi_cpu, SimResourceConfiguration()
        )

        python_pi_fd = SimFunctionDeployment(
            python_pi_fn,
            [python_pi_fn_container],
            SimScalingConfiguration(),
            deployment_ranking=DeploymentRanking([python_pi_fn_container]),
        )

        return python_pi_fd


if __name__ == "__main__":
    main()
