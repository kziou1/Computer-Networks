from socket import *
from rdt_lib import *

server_name = '10.0.0.2'
server_port = 12000
buffer_size = 2048



def fin_handler(sock, addr, last_seq):

    # CLOSE_WAIT
    sock.settimeou (0.5)
    while True:
        segment = UDPSeg(seq=last_seq+1, ack=1, flag=ACK)
        sock.sendto(segment.encapsulation(), addr)

        try:
            recv_bytes, addr = sock.recvfrom(buffer_size)
            segment = decapsulation(recv_bytes)

            if (not segment) or (not segment.is_ack()):
                print("Unexpected segment.")
                continue

            if segment and segment.is_fin():
                print("Double FIN received. Resending ACK...")
                continue

        except timeout:
            break
    
    sock.settimeout(0.4)
    while True:
        # LAST_ACK
        print("FIN sent.")
        segment = UDPSeg(seq=0, ack=ACK, flag=FIN)
        sock.sendto(segment.encapsulation(), addr)

        try:
            recv_bytes, addr = sock.recvfrom(buffer_size)
            segment = decapsulation(recv_bytes)

            if segment and segment.is_ack():
                print("Received ACK. Ending connection.")
                break

        except timeout:
            # CLOSED
            print("Did not receive ACK. Resending...")

def receive_file(sock, start_seq):
    expected_seq = start_seq

    with open('received_file.pdf', 'wb') as fd:
        while True:
            try:
                # Disable timer when receiving data
                sock.settimeout(None)

                recv_bytes, addr = sock.recvfrom(buffer_size)
                rdt_recv = decapsulation(recv_bytes)

                if not rdt_recv: continue

                if rdt_recv.is_fin():
                    print("Received FIN. Closing connection.")
                    return expected_seq

                # If data has the expected sequence write it in the file and sent ACK
                if rdt_recv.seq == expected_seq:
                    fd.write(rdt_recv.data)

                    segment = UDPSeg(seq=0, ack=expected_seq, flag=ACK, data=b'')
                    sock.sendto(segment.encapsulation(), addr)

                    expected_seq += 1

                # Else resend ACK with the last acknowledged sequence
                else:
                    print(f"Unexpected seq_num: {rdt_recv.seq} (Expected: {expected_seq})")
                    if expected_seq == start_seq:
                        re_ack = UDPSeg(seq=0, ack=start_seq - 1, flag=ACK, data=b'')
                    else:
                        re_ack = UDPSeg(seq=0, ack=expected_seq - 1, flag=ACK, data=b'')

                    sock.sendto(re_ack.encapsulation(), addr)
            except Exception as e:
                print(f"Error: {e}")
                return expected_seq


def server_handshake(server_isn, sock, addr_ref, max_attempts=10):
    sock.settimeout(None)

    # 1st handshake
    recv_bytes, addr = sock.recvfrom(buffer_size)
    segment = decapsulation(recv_bytes)

    if (not segment) or (not segment.is_syn()):
        print("Did not receive SYN segment...")
        return -1
    print("Received SYN")

    print(f"Received SYN from {addr}, Seq={segment.seq}")
    client_isn = segment.seq
    addr_ref[0] = addr

    # 2nd handshake
    sock.settimeout(0.5)

    syn_ack_seg = UDPSeg(seq=server_isn, ack=client_isn + 1, flag=SYN | ACK, data=b'')
    bytes_to_send = syn_ack_seg.encapsulation()

    sock.sendto(bytes_to_send, addr)
    print("Sent SYN-ACK")

    # 3rd handshake
    # Tries to connect with client
    for attempts in range(max_attempts):
        try:
            recv_bytes, client_addr = sock.recvfrom(buffer_size)
            segment = decapsulation(recv_bytes)
            client_isn = segment.seq

            if not segment:
                continue

            # If we got the ACK package and return the next sequence as the server_isn+1
            if segment.is_ack() and segment.ack == server_isn + 1:
                print("Received ACK. Connection Established.")
                sock.settimeout(None)
                return client_isn + 1

            # If ACK was lost and data was sent from client
            # we reject the data and return to start reading
            if segment.flag & DATA:
                print(f"Received DATA (Seq={segment.seq}). Implicit ACK accepted.")
                sock.settimeout(None)
                return segment.seq

        except timeout:
            attempts += 1
            print(f"Timeout. Resending SYN-ACK (Attempt {attempts})...")
            sock.sendto(bytes_to_send, addr)

    print("Handshake failed after max retries.")
    return -1


def main():
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind((server_name, server_port))
    print(f"Server listening on {server_name}:{server_port}")

    # 1. Wait for connections
    client_addr = [None]
    start_seq = -1

    # Try to connect with client
    while start_seq == -1:
        start_seq = server_handshake(2004, sock, client_addr)
        if start_seq == -1:
            print("Server: Failed handshake. Retrying...")

    print(f"Connected with client {client_addr[0]}")

    # 2. Get PDF fragments
    last_seq = receive_file(sock, start_seq)

    # 3. Got FIN close connection
    fin_handler(sock, client_addr[0], last_seq)

    sock.close()

if __name__ == "__main__":
    main()


