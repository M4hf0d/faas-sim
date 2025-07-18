from collections import defaultdict
from typing import Dict

import pandas as pd
from ether.core import Capacity
from skippy.core.model import SchedulingResult

from sim.core import Environment
from sim.faas import (
    FunctionContainer,
    FunctionRequest,
    FunctionReplica,
    FunctionDeployment,
)
from sim.logging import RuntimeLogger, NullLogger
from sim.resource import ResourceUtilization


class Metrics:
    """
    Instrumentation and trace logger.
    """

    invocations: Dict[str, int]
    total_invocations: int
    last_invocation: Dict[str, float]
    utilization: Dict[str, Dict[str, float]]

    def __init__(self, env: Environment, log: RuntimeLogger = None) -> None:
        super().__init__()
        self.env: Environment = env
        self.logger: RuntimeLogger = log or NullLogger()
        self.total_invocations = 0
        self.invocations = defaultdict(int)
        self.last_invocation = defaultdict(int)
        self.utilization = defaultdict(lambda: defaultdict(float))

    def log(self, metric, value, **tags):
        return self.logger.log(metric, value, **tags)

    def log_function_deployment(self, fn: FunctionDeployment):
        """
        Logs the functions name, related container images and their metadata
        """
        # TODO log metadata/handle function definitions
        # use log_function_definition
        record = {"name": fn.name}
        self.log("function_deployments", record, type="deploy")

    def log_function_definition(self, fn_name: str, fn: FunctionContainer):
        """
        Logs the functions name, related container images and their metadata
        """
        record = {"name": fn_name, "image": fn.image}
        # TODO fix clustercontext
        image_state = self.env.cluster.image_states[fn.image]
        for arch, size in image_state.size.items():
            record[f"size_{arch}"] = size

            self.log("functions", record, type="deploy")

    def log_function_replica(self, replica: FunctionReplica):
        for container in replica.pod.spec.containers:
            record = {
                "name": replica.function.name,
                "pod": replica.pod.name,
                "image": container.image,
            }
            # TODO fix clustercontext, maybe this is unnecessary as log_function_definition already logs the image
            # image_state = self.env.cluster.image_states[container.image]
            # for arch, size in image_state.size.items():
            #     record[f'size_{arch}'] = size

            self.log("function_replicas", record, replica_id=id(replica))

    def log_flow(self, num_bytes, duration, source, sink, action_type):
        self.log(
            "flow",
            value={"bytes": num_bytes, "duration": duration},
            source=source.name,
            sink=sink.name,
            action_type=action_type,
        )

    def log_network(self, num_bytes, data_type, link):
        tags = dict(link.tags)
        tags["data_type"] = data_type

        self.log("network", num_bytes, **tags)

    def log_scaling(self, function_name, replicas):
        self.log("scale", replicas, function_name=function_name)

    def log_invocation(
        self,
        function_name,
        function_image,
        node_name,
        t_wait,
        t_start,
        t_exec,
        replica_id,
        **kwargs,
    ):
        function = self.env.faas.get_function_index()[function_image]
        mem = function.get_resource_requirements().get("memory")

        self.log(
            "invocations",
            {
                "t_wait": t_wait,
                "t_exec": t_exec,
                "t_start": t_start,
                "memory": mem,
                **kwargs,
            },
            function_name=function_name,
            function_image=function_image,
            node=node_name,
            replica_id=replica_id,
        )

    def log_fet(
        self,
        function_name,
        function_image,
        node_name,
        t_fet_start,
        t_fet_end,
        replica_id,
        request_id,
        **kwargs,
    ):
        # TODO design more general? wait/degradation are specific to queue simulator/performance degradation
        self.log(
            "fets",
            {"t_fet_start": t_fet_start, "t_fet_end": t_fet_end, **kwargs},
            function_name=function_name,
            function_image=function_image,
            node=node_name,
            replica_id=replica_id,
            request_id=request_id,
        )

    def log_function_resource_utilization(
        self, replica: FunctionReplica, utilization: ResourceUtilization
    ):
        node = replica.node
        copy = utilization.copy()
        resources = self.__calculate_util(node.capacity, copy)
        self.log(
            "function_utilization", resources, node=node.name, replica_id=id(replica)
        )

    def log_resource_utilization(
        self, node_name: str, capacity: Capacity, utilization: ResourceUtilization
    ):
        resources = self.__calculate_util(capacity, utilization)
        self.log("node_utilization", resources, node=node_name)

    def __calculate_util(self, capacity, utilization):
        update = {
            "cpu_util": (
                utilization.get_resource("cpu") / capacity.cpu_millis
                if utilization.get_resource("cpu") is not None
                else 0
            ),
            "mem_util": (
                utilization.get_resource("memory") / capacity.memory
                if utilization.get_resource("memory") is not None
                else 0
            ),
        }
        resources = utilization.list_resources()
        resources.update(update)
        return resources

    def log_start_exec(
        self, request: FunctionRequest, replica: FunctionReplica, **kwargs
    ):
        self.invocations[replica.function.name] += 1
        self.total_invocations += 1
        self.last_invocation[replica.function.name] = self.env.now

    def log_stop_exec(
        self, request: FunctionRequest, replica: FunctionReplica, **kwargs
    ):
        pass

    def log_deploy(self, replica: FunctionReplica):
        self.log(
            "replica_deployment",
            "deploy",
            function_name=replica.function.name,
            node_name=replica.node.name,
            replica_id=id(replica),
        )

    def log_startup(self, replica: FunctionReplica):
        self.log(
            "replica_deployment",
            "startup",
            function_name=replica.function.name,
            node_name=replica.node.name,
            replica_id=id(replica),
        )

    def log_setup(self, replica: FunctionReplica):
        self.log(
            "replica_deployment",
            "setup",
            function_name=replica.function.name,
            node_name=replica.node.name,
            replica_id=id(replica),
        )

    def log_finish_deploy(self, replica: FunctionReplica):
        self.log(
            "replica_deployment",
            "finish",
            function_name=replica.function.name,
            node_name=replica.node.name,
            replica_id=id(replica),
        )

    def log_teardown(self, replica: FunctionReplica):
        name = replica.fn_name
        node_name = replica.node.name
        self.log(
            "replica_deployment",
            "teardown",
            function_name=name,
            node_name=node_name,
            replica_id=id(replica),
        )

    def log_function_deployment_lifecycle(self, fn: FunctionDeployment, event: str):
        self.log(
            "function_deployment_lifecycle", event, name=fn.name, function_id=id(fn)
        )

    def log_queue_schedule(self, replica: FunctionReplica):
        name = replica.fn_name
        image = replica.image
        self.log(
            "schedule", "queue", function_name=name, image=image, replica_id=id(replica)
        )

    def log_start_schedule(self, replica: FunctionReplica):
        name = replica.fn_name
        image = replica.image
        self.log(
            "schedule", "start", function_name=name, image=image, replica_id=id(replica)
        )

    def log_finish_schedule(self, replica: FunctionReplica, result: SchedulingResult):
        if not result.suggested_host:
            node_name = "None"
        else:
            node_name = result.suggested_host.name

        self.log(
            "schedule",
            "finish",
            function_name=replica.function.name,
            image=replica.container.image,
            node_name=node_name,
            successful=node_name != "None",
            replica_id=id(replica),
        )

    def log_function_deploy(self, replica: FunctionReplica):
        fn = replica.container
        image = replica.image
        name = replica.fn_name
        self.log(
            "function_deployment",
            "deploy",
            name=name,
            image=image,
            function_id=id(fn),
            node=replica.node.name,
        )

    def log_function_suspend(self, replica: FunctionReplica):
        fn = replica.container
        image = replica.image
        name = replica.fn_name
        self.log(
            "function_deployment",
            "suspend",
            name=name,
            image=image,
            function_id=id(fn),
            node=replica.node.name,
        )

    def log_function_remove(self, replica: FunctionReplica):
        fn = replica.function
        image = replica.image
        name = replica.fn_name
        self.log(
            "function_deployment",
            "remove",
            name=name,
            image=image,
            function_id=id(fn),
            node=replica.node.name,
        )

    def get(self, name, **tags):
        return self.logger.get(name, **tags)

    @property
    def clock(self):
        return self.clock

    @property
    def records(self):
        return self.logger.records

    def extract_dataframe(self, measurement: str):
        data = list()

        for record in self.records:
            if record.measurement != measurement:
                continue

            r = dict()
            r["time"] = record.time
            for k, v in record.fields.items():
                r[k] = v
            for k, v in record.tags.items():
                r[k] = v

            data.append(r)
        df = pd.DataFrame(data)

        if len(data) == 0:
            return df

        df.index = pd.DatetimeIndex(pd.to_datetime(df["time"]))
        del df["time"]
        return df

class PowerMetrics:
    """Track power consumption and energy usage"""
    
    def __init__(self):
        self.power_samples = []
        self.energy_accumulation = {}  # Track cumulative energy per node
        self.last_timestamp = {}       # Track last measurement time per node
        
    def record_power_sample(self, timestamp: float, node_name: str, node_type: str,
                          cpu_util: float, gpu_util: float, network_util: float, 
                          memory_util: float, power_watts: float):
        """Record a power measurement sample"""
        
        # Calculate energy since last measurement
        if node_name in self.last_timestamp:
            time_delta = timestamp - self.last_timestamp[node_name]
            energy_joules = power_watts * time_delta
            
            if node_name not in self.energy_accumulation:
                self.energy_accumulation[node_name] = 0.0
            self.energy_accumulation[node_name] += energy_joules
        else:
            energy_joules = 0.0
            self.energy_accumulation[node_name] = 0.0
            
        self.last_timestamp[node_name] = timestamp
        
        # Store the sample
        sample = {
            'timestamp': timestamp,
            'node': node_name,
            'node_type': node_type,
            'cpu_utilization': cpu_util,
            'gpu_utilization': gpu_util,
            'network_utilization': network_util,
            'memory_utilization': memory_util,
            'power_watts': power_watts,
            'energy_delta_joules': energy_joules,
            'cumulative_energy_joules': self.energy_accumulation[node_name],
            'cumulative_energy_wh': self.energy_accumulation[node_name] / 3600.0
        }
        
        self.power_samples.append(sample)
        return sample
        
    def get_total_energy(self) -> float:
        """Get total energy consumption across all nodes in Joules"""
        return sum(self.energy_accumulation.values())
        
    def get_node_energy(self, node_name: str) -> float:
        """Get energy consumption for specific node in Joules"""
        return self.energy_accumulation.get(node_name, 0.0)
        
    def to_dataframe(self):
        """Convert power samples to DataFrame for analysis"""
        import pandas as pd
        return pd.DataFrame(self.power_samples)