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


class TutorialTopo(Topo):
    """2x2 fabric topology"""

    def __init__(self, *args, **kwargs):
        Topo.__init__(self, *args, **kwargs)

        # Leaves
        # gRPC port 50001
        leaf1 = self.addSwitch('leaf1', cls=StratumBmv2Switch, cpuport=CPU_PORT, loglevel='debug')
        # gRPC port 50002
        leaf2 = self.addSwitch('leaf2', cls=StratumBmv2Switch, cpuport=CPU_PORT)

        # Spines
        # gRPC port 50003
        spine1 = self.addSwitch('spine1', cls=StratumBmv2Switch, cpuport=CPU_PORT)
        # gRPC port 50004
        spine2 = self.addSwitch('spine2', cls=StratumBmv2Switch, cpuport=CPU_PORT)

        # Switch Links
        self.addLink(spine1, leaf1)
        self.addLink(spine1, leaf2)
        self.addLink(spine2, leaf1)
        self.addLink(spine2, leaf2)

        h1 = self.addHost('h1', cls=IPv4Host, mac="00:00:00:00:00:10",
                          ipv4='10.0.2.1/24', ipv4_gw='10.0.2.254')
        h2 = self.addHost('h2', cls=IPv4Host, mac="00:00:00:00:00:20",
                          ipv4='10.0.2.2/24', ipv4_gw='10.0.2.254')
        self.addLink(h1, leaf1)  # port 3
        self.addLink(h2, leaf1)  # port 4

        h3 = self.addHost('h3', cls=IPv4Host, mac="00:00:00:00:00:30",
                          ipv4='10.0.3.1/24', ipv4_gw='10.0.3.254')
        h4 = self.addHost('h4', cls=IPv4Host, mac="00:00:00:00:00:40",
                          ipv4='10.0.3.2/24', ipv4_gw='10.0.3.254')
        self.addLink(h3, leaf2)  # port 3
        self.addLink(h4, leaf2)  # port 4


def main():
    net = Mininet(topo=TutorialTopo(), controller=None)
    net.start()
    CLI(net)
    net.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Mininet topology script for 2x2 fabric with stratum_bmv2 and IPv4 hosts')
    args = parser.parse_args()
    setLogLevel('info')

    main()
