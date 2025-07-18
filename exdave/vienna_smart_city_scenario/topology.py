import random

from ether.blocks import nodes
from ether.blocks.cells import IoTComputeBox, BusinessIsp
from ether.blocks.nodes import counters, create_node
from ether.cell import LANCell, SharedLinkCell, UpDownLink
from ether.core import Connection
from ether.qos import latency
from ether.vis import draw_basic
from sim.faas.util.constant import (
    zone_label,
    controller_role_label,
    worker_role_label,
    client_role_label,
)
from matplotlib import pyplot as plt

from ext.raith21.etherdevices import create_xeoncpu, create_xeongpu
from sim.topology import Topology


class SmallCloudlet(LANCell):
    def __init__(self, nodes, backhaul=None) -> None:
        self.nodes = nodes

        super().__init__(nodes, backhaul=backhaul)

    def _create_identity(self):
        self.nr = next(counters["cloudlet"])
        self.name = "cloudlet_%d" % self.nr
        self.switch = "switch_%s" % self.name

    def _create_rack(self):
        return LANCell(self.nodes, backhaul=self.switch)


class CloudSenario:

    def __init__(self, backhaul: str):
        self.backhaul = backhaul

    def materialize(self, topology: Topology):
        cluster = "Cloud"
        backhaul = self.backhaul
        controller_node = create_xeoncpu()
        controller_node.labels[controller_role_label] = "true"

        cloudvm_0 = create_xeoncpu()
        cloudvm_1 = create_xeoncpu()
        cloudvm_2 = create_xeoncpu()

        cloud_nodes = [controller_node, cloudvm_0, cloudvm_1, cloudvm_2]

        for node in cloud_nodes:
            node.labels[worker_role_label] = "true"
            node.labels[zone_label] = cluster

        cloudlet = SharedLinkCell(
            [
                SmallCloudlet(
                    nodes=cloud_nodes,
                    backhaul=UpDownLink(10000, 10000, self.backhaul),
                )
            ],
            backhaul=BusinessIsp(backhaul),
        )
        cloudlet.materialize(topology)


class Clients(LANCell):
    def __init__(self, zone: str, clients=1, backhaul=None) -> None:
        self.clients = clients
        self.nucs = [nodes.nuc() for _ in range(clients)]
        for rpi in self.nucs:
            rpi.labels[client_role_label] = "true"
            rpi.labels[zone_label] = zone
        super().__init__(self.nucs, backhaul=backhaul)

    def _create_clients(self):
        return LANCell(self.nucs, backhaul=self.switch)


class LocalWifi(UpDownLink):
    def __init__(self, backhaul="internet") -> None:
        super().__init__(500, 500, backhaul, latency.wlan)


class IoTBoxScenario:

    def __init__(self, backhaul: str):
        self.backhaul = backhaul

    def materialize(self, topology: Topology):
        cluster = "IoT-Box"
        controller_node = create_xeoncpu()
        controller_node.labels[controller_role_label] = "true"
        controller_node.labels[worker_role_label] = "true"

        nano_node = nodes.nano()
        nano_node.labels[worker_role_label] = "true"

        nx_node = nodes.nx()
        nx_node.labels[worker_role_label] = "true"

        nx_node_1 = nodes.nx()
        nx_node_1.labels[worker_role_label] = "true"

        nx_node_2 = nodes.nx()
        nx_node_2.labels[worker_role_label] = "true"

        tx2_node = nodes.tx2()
        tx2_node.labels[worker_role_label] = "true"

        nuc_node = nodes.nuc()
        nuc_node.labels[client_role_label] = "true"

        topology_nodes = [
            controller_node,
            nano_node,
            nx_node,
            nx_node_1,
            nx_node_2,
            tx2_node,
        ]

        for node in topology_nodes:
            node.labels[zone_label] = cluster

        box = IoTComputeBox(nodes=topology_nodes)

        cell = SharedLinkCell(
            nodes=[box],
            shared_bandwidth=1000,
        )
        iotbox_cell = LANCell([cell], backhaul=BusinessIsp(self.backhaul))

        iotbox_cell.materialize(topology)

        clients = Clients(
            cluster,
            backhaul=LocalWifi(backhaul=iotbox_cell.switch),
        )
        clients.materialize(topology)


class CloudletScenario:
    def __init__(self, backhaul: str):
        self.backhaul = backhaul

    def materialize(self, topology: Topology):
        cluster = "Cloudlet"

        controller_node = create_xeoncpu()
        controller_node.labels[controller_role_label] = "true"
        controller_node.labels[worker_role_label] = "true"

        xeon_node_0 = create_xeoncpu()
        xeon_node_0.labels[worker_role_label] = "true"

        xeon_node_1 = create_xeoncpu()
        xeon_node_1.labels[worker_role_label] = "true"

        xeon_node_2 = create_xeoncpu()
        xeon_node_2.labels[worker_role_label] = "true"

        xeon_gpu = create_xeongpu()
        xeon_gpu.labels[worker_role_label] = "true"

        nuc_node = nodes.nuc()
        nuc_node.labels[client_role_label] = "true"

        topology_nodes = [
            controller_node,
            xeon_node_0,
            xeon_node_1,
            xeon_node_2,
            xeon_gpu,
            nuc_node,
        ]

        for node in topology_nodes:
            node.labels[zone_label] = cluster

        cloudlet = SharedLinkCell(
            [
                SmallCloudlet(
                    nodes=topology_nodes,
                    backhaul=UpDownLink(10000, 10000, self.backhaul),
                )
            ],
            backhaul=BusinessIsp(self.backhaul),
        )

        cloudlet_cell = LANCell([cloudlet], backhaul=BusinessIsp(self.backhaul))

        cloudlet_cell.materialize(topology)

        clients = Clients(
            cluster,
            backhaul=LocalWifi(backhaul=cloudlet_cell.switch),
        )
        clients.materialize(topology)


class ViennaSmartCityScenario:

    def materialize(self, topology: Topology, max_districts):
        cloud_backhaul = "internet_vie"
        for district in range(1, max_districts):
            district_backhaul = f"internet_vie_{district}_district"
            latency = random.randint(30, 200)
            topology.add_connection(
                Connection(cloud_backhaul, district_backhaul, latency=latency)
            )
            is_cloudlet = random.random() <= 0.5
            if is_cloudlet:
                CloudletScenario(district_backhaul).materialize(topology)
            else:
                IoTBoxScenario(district_backhaul).materialize(topology)
        CloudSenario(cloud_backhaul).materialize(topology)


def vienna_smart_city_topology(max_districts: int) -> Topology:
    t = Topology()
    ViennaSmartCityScenario().materialize(t, max_districts)
    t.init_docker_registry()
    return t


def main():
    topology = vienna_smart_city_topology(10)
    draw_basic(topology)
    fig = plt.gcf()
    fig.set_size_inches(25.5, 15.5)
    plt.show()  # display


if __name__ == "__main__":
    main()
