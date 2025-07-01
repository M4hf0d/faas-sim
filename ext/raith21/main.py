#!/usr/bin/env python
# coding: utf-8
import logging
import random

import numpy as np
import argparse
import sys
from examples.analysis.report import main as report_main
from skippy.core.scheduler import Scheduler  # Kubernetes-inspired scheduler
from skippy.core.storage import StorageIndex  # Tracks data locations in the network

# Import Raith21-specific modules
from ext.raith21 import images  # Container image definitions for AI workloads
from ext.raith21.benchmark.constant import (
    ConstantBenchmark,
)  # Defines constant rate workloads
from ext.raith21.characterization import (
    get_raith21_function_characterizations,
)  # Function behavior models
from ext.raith21.deployments import (
    create_all_deployments,
)  # Creates function deployment specs
from ext.mhfd.deployments import (
    create_smart_city_deployments,
    create_custom_smart_city_deployments
)
from ext.mhfd.scbenchmark import create_smart_city_constant_benchmark


from ext.raith21.etherdevices import (
    convert_to_ether_nodes,
)  # Converts device specs to network nodes
from ext.raith21.fet import (
    ai_execution_time_distributions,
)  # Function execution time data
from ext.raith21.functionsim import (
    AIPythonHTTPSimulatorFactory,
)  # Function execution simulator
from ext.raith21.generator import generate_devices  # Creates heterogeneous device specs
from ext.raith21.generators.cloudcpu import (
    cloudcpu_settings,
)  # Device configuration settings
from ext.raith21.generators.edgegpu import edgegpu_settings  # Device configuration settings
from ext.raith21.generators.edgetpu import edgetpu_settings
from ext.raith21.generators.edgecloudlet import edgecloudlet_settings
from ext.raith21.generators.cloudcpu import cloudcpu_settings
from ext.raith21.oracles import Raith21ResourceOracle, Raith21FetOracle
from ext.raith21.predicates import CanRunPred, NodeHasAcceleratorPred, NodeHasFreeGpu, NodeHasFreeTpu
from ext.raith21.resources import ai_resources_per_node_image
from ext.raith21.topology import urban_sensing_topology
from ext.raith21.util import vanilla
from sim.core import Environment
from sim.docker import ContainerRegistry
from sim.faas.system import DefaultFaasSystem
from sim.faassim import Simulation
from sim.logging import SimulatedClock, RuntimeLogger
from sim.metrics import Metrics
from sim.skippy import SimulationClusterContext

np.random.seed(1234)
random.seed(1234)
logging.basicConfig(level=logging.INFO)

# Generate heterogeneous edge and cloud devices
num_devices = 500  # Min 24 - Controls simulation scale
devices = generate_devices(num_devices, cloudcpu_settings)
ether_nodes = convert_to_ether_nodes(devices)  # Convert to network topology nodes

scenario = "custom"  # Start with default scenario


# Create oracles for predicting execution times and resource requirements
fet_oracle = Raith21FetOracle(
    ai_execution_time_distributions
)  # Function Execution Time oracle
resource_oracle = Raith21ResourceOracle(
    ai_resources_per_node_image
)  # Resource usage oracle

# Set up function deployments and container images
# deployments = list(
#     create_all_deployments(fet_oracle, resource_oracle).values()
# )  # Function deployment specs
# all_deployments = create_all_deployments(fet_oracle, resource_oracle)

# # Choose your specific function pool
# selected_functions = [
#     "resnet50-inference",     # High compute inference
#     "mobilenet-inference",    # Lightweight inference  
#     "speech-inference",       # Audio processing
#     "resnet50-training",    # Comment out heavy training
#     "resnet50-preprocessing" # Comment out preprocessing
# ]

# # Filter deployments to only include selected functions
# deployments = [all_deployments[func] for func in selected_functions if func in all_deployments]

# print("Selected functions for simulation:")
# for func_name in selected_functions:
#     if func_name in all_deployments:
#         print(f"  ✓ {func_name}")
#     else:
#         print(f"  ✗ {func_name} (not available)")



function_images = images.all_ai_images 

predicates = []
predicates.extend(
    Scheduler.default_predicates
)  # Basic resource and selector predicates
predicates.extend(
    [
        # CanRunPred(
        #     fet_oracle, resource_oracle
        # ),  # Filter nodes where function can execute efficiently
        NodeHasAcceleratorPred(),  # Filter for nodes with hardware accelerators
        NodeHasFreeGpu(),  # Filter for nodes with available GPU capacity
        # NodeHasFreeTpu(),  # Filter for nodes with available TPU capacity
    ]
)

priorities = vanilla.get_priorities()

sched_params = {
    'percentage_of_nodes_to_score': 100,
    'priorities': priorities,
    'predicates': predicates
}

# Set workload pattern - constant rate of requests
# benchmark = ConstantBenchmark(
#     "mixed", duration=500, rps=1000
# )  # rps requests/second for duration seconds


# Replace benchmark creation with:
scenario = "default"  # "default", "intensive", "distributed", "custom"

if scenario == "custom":
    custom_counts = {
        "resnet50-inference": 8,      
        "speech-inference": 6,        
        "resnet50-preprocessing": 8,  
        "python-pi": 6,               
        "fio": 4,                     
    }
    benchmark = create_smart_city_constant_benchmark(
        duration=500,
        total_rps=1200,
        scenario="custom",
        custom_counts=custom_counts
    )
else:
    benchmark = create_smart_city_constant_benchmark(
        duration=500,
        total_rps=1000,
        scenario=scenario
    )

# Initialize topology
storage_index = StorageIndex()
topology = urban_sensing_topology(ether_nodes, storage_index)

# Initialize environment
env = Environment()

env.simulator_factory = AIPythonHTTPSimulatorFactory(
    get_raith21_function_characterizations(resource_oracle, fet_oracle))
env.metrics = Metrics(env, log=RuntimeLogger(SimulatedClock(env)))
env.topology = topology
env.faas = DefaultFaasSystem(env, scale_by_requests=True)
env.container_registry = ContainerRegistry()
env.storage_index = storage_index
env.cluster = SimulationClusterContext(env)
env.scheduler = Scheduler(env.cluster, **sched_params)

sim = Simulation(env.topology, benchmark, env=env)
result = sim.run()

dfs = {
    "invocations_df": sim.env.metrics.extract_dataframe('invocations'),
    "scale_df": sim.env.metrics.extract_dataframe('scale'),
    "schedule_df": sim.env.metrics.extract_dataframe('schedule'),
    "replica_deployment_df": sim.env.metrics.extract_dataframe('replica_deployment'),
    "function_deployments_df": sim.env.metrics.extract_dataframe('function_deployments'),
    "function_deployment_df": sim.env.metrics.extract_dataframe('function_deployment'),
    "function_deployment_lifecycle_df": sim.env.metrics.extract_dataframe('function_deployment_lifecycle'),
    "functions_df": sim.env.metrics.extract_dataframe('functions'),
    "flow_df": sim.env.metrics.extract_dataframe('flow'),
    "network_df": sim.env.metrics.extract_dataframe('network'),
    "utilization_df": sim.env.metrics.extract_dataframe('utilization'),
    'fets_df': sim.env.metrics.extract_dataframe('fets')
}
print(len(dfs))
