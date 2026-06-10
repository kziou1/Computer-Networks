#!/usr/bin/python3
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
        controller=None,
        switch=OVSKernelSwitch,
        link=TCLink,
        autoStaticArp=False,
        build=False
    )

    net.build()
    net.start()

    # --- Manually reset and assign router IPs (override Mininet defaults) ---
    r1, r2, r3 = net['r1'], net['r2'], net['r3']

    # Clear any Mininet-assigned IPs
    for r in (r1, r2, r3):
        for intf in r.intfList():
            r.cmd(f'ifconfig {intf} 0')

    # Reassign correct IPs exactly as in topo3.py
    r1.cmd('ifconfig r1-eth1 10.0.1.1/24 up')
    r1.cmd('ifconfig r1-eth2 10.0.12.1/30 up')

    r2.cmd('ifconfig r2-eth1 10.0.12.2/30 up')
    r2.cmd('ifconfig r2-eth2 10.0.23.1/30 up')
    r2.cmd('ifconfig r2-eth3 10.0.2.1/24 up')

    r3.cmd('ifconfig r3-eth1 10.0.23.2/30 up')
    r3.cmd('ifconfig r3-eth2 10.0.3.1/24 up')

    info("\n=== Router interfaces reconfigured ===\n")

    # --- Enable L2 learning behavior on all switches ---
    for sw in net.switches:
        sw.cmd(f'ovs-vsctl set-fail-mode {sw.name} standalone')
        sw.cmd(f'ovs-vsctl set-controller {sw.name}')
        sw.cmd(f'ovs-ofctl del-flows {sw.name}')
        sw.cmd(f'ovs-ofctl add-flow {sw.name} actions=NORMAL')


    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()

