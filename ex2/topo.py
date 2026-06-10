#!/usr/bin/python3
"""
Custom multi-router topology for Mininet.

Topology:
    (h1,h2) -- s1 -- r1 -- r2 -- r3 -- s3 -- (h3,h4)
                              |
                             s2
                              |
                              h5
"""

from mininet.topo import Topo
from mininet.node import Node


class LinuxRouter(Node):
    """A Node with IP forwarding enabled."""
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl -w net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl -w net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()


class MyTopo(Topo):
    """Multi-router topology"""
    def __init__(self):
        Topo.__init__(self)

        # Routers
        r1 = self.addNode('r1', cls=LinuxRouter)
        r2 = self.addNode('r2', cls=LinuxRouter)
        r3 = self.addNode('r3', cls=LinuxRouter)

        # Switches for each LAN
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')

        # Hosts
        h1 = self.addHost('h1', ip='10.0.1.10/24', defaultRoute='via 10.0.1.1')
        h2 = self.addHost('h2', ip='10.0.1.11/24', defaultRoute='via 10.0.1.1')
        h3 = self.addHost('h3', ip='10.0.3.10/24', defaultRoute='via 10.0.3.1')
        h4 = self.addHost('h4', ip='10.0.3.11/24', defaultRoute='via 10.0.3.1')
        h5 = self.addHost('h5', ip='10.0.2.10/24', defaultRoute='via 10.0.2.1')

        # Connect hosts to their LAN switches
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s3)
        self.addLink(h4, s3)
        self.addLink(h5, s2)

        # Connect routers to switches (LANs)
        self.addLink(s1, r1, intfName2='r1-eth1', params2={'ip': '10.0.1.1/24'})
        self.addLink(s2, r2, intfName2='r2-eth3', params2={'ip': '10.0.2.1/24'})
        self.addLink(s3, r3, intfName2='r3-eth2', params2={'ip': '10.0.3.1/24'})

        # Router-to-router point-to-point links
        self.addLink(r1, r2,
                     intfName1='r1-eth2', params1={'ip': '10.0.12.1/30'},
                     intfName2='r2-eth1', params2={'ip': '10.0.12.2/30'})

        self.addLink(r2, r3,
                     intfName1='r2-eth2', params1={'ip': '10.0.23.1/30'},
                     intfName2='r3-eth1', params2={'ip': '10.0.23.2/30'})

