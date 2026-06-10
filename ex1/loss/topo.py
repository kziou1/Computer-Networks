#!/usr/bin/python3
from mininet.topo import Topo
from mininet.link import TCLink

class MyTopo(Topo):
    def __init__(self):

        Topo.__init__(self)

        # Add hosts
        h1 = self.addHost('h1', ip="10.0.0.1/24")
        h2 = self.addHost('h2', ip="10.0.0.2/24")

        # Add single switch
        s1 = self.addSwitch('s1')

        # 5% packet loss per link
        linkLoss = {'loss': 5}

        # Add links with loss=5%
        self.addLink(h1, s1, cls=TCLink, **linkLoss)
        self.addLink(h2, s1, cls=TCLink, **linkLoss)


topos = { 'mytopo': (lambda: MyTopo()) }

