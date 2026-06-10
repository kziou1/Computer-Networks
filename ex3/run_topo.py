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

    r1, r2, r3, r4 = net['r1'], net['r2'], net['r3'], net['r4']

    # ----------------------------------------------------------------------
    # 1. CLEAR DEFAULT MININET IPs
    # ----------------------------------------------------------------------
    for r in (r1, r2, r3, r4):
        for intf in r.intfList():
            r.cmd(f'ifconfig {intf} 0')

    info("\n=== Assigning Router Interface IPs ===\n")

    # R1
    r1.cmd('ifconfig r1-eth1 10.0.1.1/24 up')   # LAN1
    r1.cmd('ifconfig r1-eth2 10.0.12.1/30 up')  # to R2
    r1.cmd('ifconfig r1-eth3 10.0.14.1/30 up')  # to R4

    # R2
    r2.cmd('ifconfig r2-eth1 10.0.12.2/30 up')  # to R1
    r2.cmd('ifconfig r2-eth2 10.0.23.1/30 up')  # to R3
    r2.cmd('ifconfig r2-eth3 10.0.2.1/24 up')   # LAN2 (Host5)

    # R3
    r3.cmd('ifconfig r3-eth1 10.0.23.2/30 up')  # to R2
    r3.cmd('ifconfig r3-eth2 10.0.3.1/24 up')   # LAN3 (Host3)
    r3.cmd('ifconfig r3-eth3 10.0.34.2/30 up')  # to R4

    # R4
    r4.cmd('ifconfig r4-eth1 10.0.14.2/30 up')  # to R1
    r4.cmd('ifconfig r4-eth2 10.0.34.1/30 up')  # to R3

    # ----------------------------------------------------------------------
    # 2. STATIC ROUTING REMOVED AS PER EXERCISE TASK
    # ----------------------------------------------------------------------
    info("=== Static routing is disabled. Configure manually in CLI/xterm. ===\n")

    # ----------------------------------------------------------------------
    # 3. SET SWITCHES TO STANDALONE
    # ----------------------------------------------------------------------
    for sw in net.switches:
        sw.cmd(f'ovs-vsctl set-fail-mode {sw.name} standalone')
        sw.cmd(f'ovs-vsctl set-controller {sw.name} none')
        sw.cmd(f'ovs-ofctl del-flows {sw.name}')
        sw.cmd(f'ovs-ofctl add-flow {sw.name} actions=NORMAL')

    # ----------------------------------------------------------------------
    # 4. APPLY TBF BANDWIDTH LIMITS
    # ----------------------------------------------------------------------
    info("=== Applying Bandwidth Limits (10/20 Mbps) ===\n")
    
    slow_links = {
        "r1-eth2", "r2-eth1", 
        "r2-eth2", "r3-eth1", 
        "r2-eth3"             
    }

    for node in net.hosts + net.switches + [r1, r2, r3, r4]:
        for intf in node.intfList():
            iface = str(intf)
            rate = "10mbit" if iface in slow_links else "20mbit"
            # Change this in your run_topo.py
            node.cmd(
                f"tc qdisc replace dev {iface} parent root handle 1: "  # Changed add to replace
                f"tbf rate {rate} burst 32kbit latency 50ms"           # Removed 2>/dev/null
            )

    info("=== Topology Ready. Opening CLI... ===\n")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()
