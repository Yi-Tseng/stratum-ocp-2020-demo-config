#!/usr/bin/python
#
# Copyright 2020-present Open Networking Foundation
#
# SPDX-License-Identifier: Apache-2.0
#

import argparse

from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import Host
from mininet.topo import Topo
from stratum import StratumBmv2Switch

CPU_PORT = 255

class IPv4Host(Host):

    def config(self, ipv4, ipv4_gw=None, **params):
        super(IPv4Host, self).config(**params)
        self.cmd('ip -4 addr flush dev %s' % self.defaultIntf())
        self.cmd('ip -4 addr flush dev %s' % self.defaultIntf())
        self.cmd('ip -4 addr add %s dev %s' % (ipv4, self.defaultIntf()))
        if ipv4_gw:
            self.cmd('ip -4 route add default via %s' % ipv4_gw)
        # Disable offload
        for attr in ["rx", "tx", "sg"]:
            cmd = "/sbin/ethtool --offload %s %s off" % (self.defaultIntf(), attr)
            self.cmd(cmd)

        def updateIP():
            return ipv4.split('/')[0]

        self.defaultIntf().updateIP = updateIP

    def terminate(self):
        super(IPv4Host, self).terminate()


class DemoTopo(Topo):
    """2 2x2 fabric topology"""

    def __init__(self, *args, **kwargs):
        Topo.__init__(self, *args, **kwargs)

        # Leaves
        # gRPC port 50001
        leaf1 = self.addSwitch('leaf1', cls=StratumBmv2Switch, cpuport=CPU_PORT)
        # gRPC port 50002
        leaf2 = self.addSwitch('leaf2', cls=StratumBmv2Switch, cpuport=CPU_PORT)
        # gRPC port 50003
        leaf3 = self.addSwitch('leaf3', cls=StratumBmv2Switch, cpuport=CPU_PORT)
        # gRPC port 50004
        leaf4 = self.addSwitch('leaf4', cls=StratumBmv2Switch, cpuport=CPU_PORT)

        # Spines
        # gRPC port 50005
        spine1 = self.addSwitch('spine1', cls=StratumBmv2Switch, cpuport=CPU_PORT)
        # gRPC port 50006
        spine2 = self.addSwitch('spine2', cls=StratumBmv2Switch, cpuport=CPU_PORT)
        # gRPC port 50007
        spine3 = self.addSwitch('spine3', cls=StratumBmv2Switch, cpuport=CPU_PORT)
        # gRPC port 50008
        spine4 = self.addSwitch('spine4', cls=StratumBmv2Switch, cpuport=CPU_PORT)

        # Switch Links
        self.addLink(spine1, leaf1)
        self.addLink(spine1, leaf2)
        self.addLink(spine2, leaf1)
        self.addLink(spine2, leaf2)

        self.addLink(spine3, leaf3)
        self.addLink(spine3, leaf4)
        self.addLink(spine4, leaf3)
        self.addLink(spine4, leaf4)

        # Links between spines
        self.addLink(spine1, spine3)
        self.addLink(spine2, spine4)

        h1 = self.addHost('h1', cls=IPv4Host, mac="00:0c:00:00:00:10",
                          ipv4='10.0.2.1/24', ipv4_gw='10.0.2.254')
        h2 = self.addHost('h2', cls=IPv4Host, mac="00:0c:00:00:00:20",
                          ipv4='10.0.2.2/24', ipv4_gw='10.0.2.254')
        self.addLink(h1, leaf1)  # port 3
        self.addLink(h2, leaf1)  # port 4

        h3 = self.addHost('h3', cls=IPv4Host, mac="00:0c:00:00:00:30",
                          ipv4='10.0.3.1/24', ipv4_gw='10.0.3.254')
        h4 = self.addHost('h4', cls=IPv4Host, mac="00:0c:00:00:00:40",
                          ipv4='10.0.3.2/24', ipv4_gw='10.0.3.254')
        self.addLink(h3, leaf2)  # port 3
        self.addLink(h4, leaf2)  # port 4

        h5 = self.addHost('h5', cls=IPv4Host, mac="00:0f:00:00:00:10",
                          ipv4='10.1.2.1/24', ipv4_gw='10.1.2.254')
        h6 = self.addHost('h6', cls=IPv4Host, mac="00:0f:00:00:00:20",
                          ipv4='10.1.2.2/24', ipv4_gw='10.1.2.254')
        self.addLink(h5, leaf3)  # port 3
        self.addLink(h6, leaf3)  # port 4

        h7 = self.addHost('h7', cls=IPv4Host, mac="00:0f:00:00:00:30",
                          ipv4='10.1.3.1/24', ipv4_gw='10.1.3.254')
        h8 = self.addHost('h8', cls=IPv4Host, mac="00:0f:00:00:00:40",
                          ipv4='10.1.3.2/24', ipv4_gw='10.1.3.254')
        self.addLink(h7, leaf4)  # port 3
        self.addLink(h8, leaf4)  # port 4

def main():
    net = Mininet(topo=DemoTopo(), controller=None)
    net.start()
    CLI(net)
    net.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Mininet topology script for 2x2 fabric with stratum_bmv2 and IPv4 hosts')
    args = parser.parse_args()
    setLogLevel('info')

    main()
