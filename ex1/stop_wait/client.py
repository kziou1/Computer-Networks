from math import trunc
from  socket import *
import time
import os
import sys
from rdt_lib import *

server_port = 12000
buffer_size = 2048

def fin_handler(sock, seq_cnt, server_name):

    while True:
        # FIN_WAIT_1
        print("File sent. Sending FIN...")
        fin_segm = UDPSeg(seq=seq_cnt, ack=ACK, flag=FIN, data=b'')
        sock.sendto(fin_segm.encapsulation(), (server_name, server_port))

        sock.settimeout(0.4)

        try:
            recv_bytes, addr = sock.recvfrom(buffer_size)
            rdt_recv = decapsulation(recv_bytes)
            next_seq = rdt_recv.seq

            if (not rdt_recv) or (not rdt_recv.is_ack()):
                print("Did not receive ACK.")
                continue

            print("Received ACK.")
            break

        except timeout:
            print("Did not receive ACK. Retrying...")

    while True:
        # FIN_WAIT_2

        try:
            recv_bytes, addr = sock.recvfrom(buffer_size)
            rdt_recv = decapsulation(recv_bytes)

            if (not rdt_recv) or (not rdt_recv.is_fin()):
                print("Did not receive FIN.")
                continue
        except timeout:
            print("Did not receive FIN...")
            continue

        # TIMED_WAIT
        sock.settimeout(0.4)
        fin_segm = UDPSeg(seq=seq_cnt, ack=next_seq, flag=ACK, data=b'')
        sock.sendto(fin_segm.encapsulation(), (server_name, server_port))

        print("Sent final ACK.")

        # Wait to for time to end
        try:
            recv_bytes, addr = sock.recvfrom(buffer_size)
            rdt_recv = decapsulation(recv_bytes)

            if rdt_recv and rdt_recv.is_fin():
                print("Got double FIN. Resending...")
                continue

        except timeout:
            # CLOSE
            print("Closing connection.")
            break

def send_file(filename, sock, server_name, file_size, mss=1024):
    seq_cnt = 1
    start_time = time.time()

    try:
        with open(filename, 'rb') as fd:
            while True:

                # Read segment
                data_read = fd.read(mss)

                if not data_read:   # If empty exit
                    break

                # Send segment and wait to receive the ACK
                rdt_segm = UDPSeg(seq=seq_cnt, ack=ACK, flag=DATA, data=data_read)
                while True:

                    sock.sendto(rdt_segm.encapsulation(), (server_name, server_port))
                    try:
                        recv_bytes, addr = sock.recvfrom(buffer_size)
                        rdt_recv = decapsulation(recv_bytes)

                        # If not expected data, reread
                        if (not rdt_recv) or (not rdt_recv.is_ack()):
                            continue

                        # If expected data move to next segment
                        if rdt_recv.ack == seq_cnt:
                            seq_cnt += 1
                            break

                    # Timeout, resent data
                    except timeout:
                        print(f"Timeout for package {seq_cnt}. Resending...")

    # Failed to open file
    except OSError as e:
        print(type(e), e)

    end_time = time.time()

    time_taken = end_time - start_time
    throughput_kbps = ((file_size / time_taken) * 8) / 1000

    print("-" * 40)
    print(f"File transfered in {time_taken: .4f} sec.")
    print(f"Average Throughput: {throughput_kbps:.2f} Kbps")
    print("-" * 40)

    return seq_cnt

def client_handshake(client_isn, sock, dest_addr, dest_port, max_attempts=5):

    # 1st handshake
    rdt_segm = UDPSeg(seq=client_isn, ack=0, flag=SYN, data=b'')

    for curr_attempt in range(max_attempts):
        sock.sendto(rdt_segm.encapsulation(), (dest_addr, dest_port))

        if curr_attempt > 0:
            print(f"Resending SYN (Attempt {curr_attempt})...")

        try:
            # 2nd handshake
            recv_bytes, addr = sock.recvfrom(buffer_size)
            segment = decapsulation(recv_bytes)

            if segment and segment.is_syn() and segment.is_ack():
                print("Received SYN-ACK")
                server_isn = segment.seq

                # 3rd handshake
                rdt_segm = UDPSeg(seq=client_isn + 1, ack=server_isn + 1, flag=ACK, data=b'')
                sock.sendto(rdt_segm.encapsulation(), (dest_addr, dest_port))
                print("Sent ACK")
                return False
            else:
                print("Received wrong segment instead of SYN-ACK.")

        except timeout:
            print("Failed to receive SYN-ACK.")

    return True

def main():
    if len(sys.argv) < 3:
        print("Incorrect arguments. Run as:\n>>python3 client.py <server_name> <filename>")
        return

    server_name = sys.argv[1]
    filename = sys.argv[2]

    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return

    file_size = os.path.getsize(filename)

    # 1 Start handshake
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.settimeout(0.2)

    if client_handshake(2004, sock, server_name, server_port):
        print("Client: Handshake failed...")
        return

    print("Handshake successful.")
    
    # 2 Send file
    sock.settimeout(0.005)
    seq_cnt = send_file(filename, sock, server_name, file_size)

    # 3 Send FIN
    fin_handler(sock, seq_cnt, server_name)

    sock.close()

if __name__ == "__main__":
    main()

