#!/usr/bin/python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from topo import MyTopo

def run():
    topo = MyTopo()

    net = Mininet(
        topo=topo,
        switch=OVSKernelSwitch,
        controller=None,
        link=TCLink
    )

    net.start()

    # Put OVS in standalone (learning-switch) mode
    for sw in net.switches:
        sw.cmd(f"ovs-vsctl set-fail-mode {sw.name} standalone")
        sw.cmd(f"ovs-vsctl del-controller {sw.name}")
        sw.cmd(f"ovs-ofctl del-flows {sw.name}")
        sw.cmd(f"ovs-ofctl add-flow {sw.name} actions=NORMAL")

    info("\n=== Network running (OVS standalone, no controller) ===\n")
    info("=== Links have 5% loss each ===\n")
    info("Try: h1 ping -c 10 h2\n\n")

    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()

