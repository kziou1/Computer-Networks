#!/usr/bin/python3
"""
Topology aligned with the visual diagram:
- Removes r1 <-> r3 link
- Removes r2 <-> r4 link
- Path 1 (Slow): r1 <-> r2 <-> r3
- Path 2 (Fast): r1 <-> r4 <-> r3
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
    """Extended Multi-router topology aligned with visual diagram."""
    def __init__(self):
        super(MyTopo, self).__init__()

        # --- 1. Nodes Setup ---
        # Routers
        r1 = self.addNode('r1', cls=LinuxRouter)
        r2 = self.addNode('r2', cls=LinuxRouter)
        r3 = self.addNode('r3', cls=LinuxRouter)
        r4 = self.addNode('r4', cls=LinuxRouter)

        # Switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')

        # Hosts
        # LAN 1: Host 1 & 2
        h1 = self.addHost('h1', ip='10.0.1.10/24', defaultRoute='via 10.0.1.1')
        h2 = self.addHost('h2', ip='10.0.1.11/24', defaultRoute='via 10.0.1.1')
        
        # LAN 2: Host 5
        h5 = self.addHost('h5', ip='10.0.2.10/24', defaultRoute='via 10.0.2.1')
        
        # LAN 3: Host 3
        h3 = self.addHost('h3', ip='10.0.3.10/24', defaultRoute='via 10.0.3.1')

        # Baseline latency
        link_params = {'delay': '1ms'}

        # --- 2. Host-to-Switch Links ---
        self.addLink(h1, s1, **link_params)
        self.addLink(h2, s1, **link_params)
        self.addLink(h5, s2, **link_params)
        self.addLink(h3, s3, **link_params)

        # --- 3. Switch-to-Router Links (Gateways) ---
        # Switch 1 -> R1 (LAN 1 Gateway)
        self.addLink(s1, r1, intfName2='r1-eth1', params2={'ip': '10.0.1.1/24'}, **link_params)

        # Switch 2 -> R2 (LAN 2 Gateway)
        self.addLink(s2, r2, intfName2='r2-eth3', params2={'ip': '10.0.2.1/24'}, **link_params)

        # Switch 3 -> R3 (LAN 3 Gateway)
        self.addLink(s3, r3, intfName2='r3-eth2', params2={'ip': '10.0.3.1/24'}, **link_params)

        # --- 4. Router-to-Router Links (Diamond Topology) ---
        
        # Upper Path (Slow path): r1 <-> r2 <-> r3
        self.addLink(r1, r2,
                     intfName1='r1-eth2', params1={'ip': '10.0.12.1/30'},
                     intfName2='r2-eth1', params2={'ip': '10.0.12.2/30'},
                     **link_params)

        self.addLink(r2, r3,
                     intfName1='r2-eth2', params1={'ip': '10.0.23.1/30'},
                     intfName2='r3-eth1', params2={'ip': '10.0.23.2/30'},
                     **link_params)

        # Lower Path (Fast path): r1 <-> r4 <-> r3
        self.addLink(r1, r4,
                     intfName1='r1-eth3', params1={'ip': '10.0.14.1/30'},
                     intfName2='r4-eth1', params2={'ip': '10.0.14.2/30'},
                     **link_params)

        self.addLink(r4, r3,
                     intfName1='r4-eth2', params1={'ip': '10.0.34.1/30'},
                     intfName2='r3-eth3', params2={'ip': '10.0.34.2/30'},
                     **link_params)

topos = {'mytopo': (lambda: MyTopo())}
