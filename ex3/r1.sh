sysctl -w net.ipv4.ip_forward=1

ip route add 10.0.2.0/24 via 10.0.12.2
ip route add 10.0.3.0/24 via 10.0.14.2
