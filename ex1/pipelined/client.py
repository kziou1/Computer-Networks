from math import trunc
from  socket import *
import time
import os
import sys
import select
from rdt_lib import *

server_port = 12000
buffer_size = 2048
client_isn = 2004

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
            print("Did not receive last FIN...")
            continue

        # TIMED_WAIT
        sock.settimeout(0.5)
        fin_segm = UDPSeg(seq=seq_cnt, ack=next_seq+1, flag=ACK, data=b'')
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

def send_file(filename, sock, server_name, file_size, init_seq, mss=1024):
    base = init_seq
    next_seq_num = init_seq
    window_size = 10

    window = {}     # Window for segments that are sent

    start_time = time.time()

    sock.setblocking(0)

    timeout_interval = 0.05
    timer_start = None

    try:
        with open(filename, 'rb') as fd:
            file_done = False

            # Read MMS segments of the file and send them
            while not file_done or len(window) > 0:

                # Inner while to fill the window buffer
                while next_seq_num < base + window_size and not file_done:
                    data_read = fd.read(mss)

                    # When all file is read
                    if not data_read:
                        file_done = True
                        break

                    rdt_segm = UDPSeg(seq=next_seq_num, ack=ACK, flag=DATA, data=data_read)
                    window[next_seq_num] = rdt_segm
                    sock.sendto(rdt_segm.encapsulation(), (server_name, server_port))

                    # When the window is empty start timer
                    if base == next_seq_num:
                        timer_start = time.time()

                    next_seq_num += 1

                # Out of inner while. Waiting to receive ACK with timeout 0.01s so we don't block forever
                ready = select.select([sock], [], [], 0.01)
                if ready[0]:
                    try:
                        recv_bytes, addr = sock.recvfrom(buffer_size)
                        rdt_recv = decapsulation(recv_bytes)

                        # If it is the right ACK
                        if rdt_recv and rdt_recv.is_ack():
                            ack_seq = rdt_recv.ack

                            # Check if the ACK got is greater that the base now
                            # (it is use in case previous ACK got lost but it is still acceptable)
                            if ack_seq >= base:

                                # Remove all previous segments in the window
                                while base <= ack_seq:
                                    if base in window:
                                        del window[base]
                                    base += 1

                                # Keep track of the oldest segment in buffer
                                if base == next_seq_num:
                                    timer_start = None
                                else:
                                    timer_start = time.time()

                    except BlockingIOError:
                        pass

                # Timer from the last segment sent till timeout.
                # If no ACK was sent then there was a timeout and all packages are resent
                if timer_start and (time.time() - timer_start > timeout_interval):
                    print(f"Timeout! Retransmitting window from seq {base} to {next_seq_num - 1}")

                    for seq in range(base, next_seq_num):
                        if seq in window:
                            sock.sendto(window[seq].encapsulation(), (server_name, server_port))

                    timer_start = time.time()

    except OSError as e:
        print(type(e), e)

    sock.setblocking(1)

    end_time = time.time()

    # Calculate throughput
    time_taken = end_time - start_time
    throughput_kbps = ((file_size / time_taken) * 8) / 1000

    print("-" * 40)
    print(f"File transfered in {time_taken: .4f} sec.")
    print(f"Average Throughput: {throughput_kbps:.2f} Kbps")
    print("-" * 40)

    return next_seq_num

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
            rdt_segm = decapsulation(recv_bytes)

            if rdt_segm and rdt_segm.is_syn() and rdt_segm.is_ack():
                print("Received SYN-ACK")
                server_isn = rdt_segm.seq

                # 3rd handshake
                rdt_segm = UDPSeg(seq=client_isn + 1, ack=server_isn + 1, flag=ACK, data=b'')
                sock.sendto(rdt_segm.encapsulation(), (dest_addr, dest_port))
                print("Sent ACK")
                return False

        except timeout:
            curr_attempt += 1

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
    sock.settimeout(0.005)

    if client_handshake(client_isn, sock, server_name, server_port):
        print("Client: Handshake failed...")
        return

    print("Handshake successful.")

    # 2 Send file
    start_seq = client_isn + 2
    seq_cnt = send_file(filename, sock, server_name, file_size, start_seq)

    # 3 Send FIN
    fin_handler(sock, seq_cnt, server_name)

    sock.close()

if __name__ == "__main__":
    main()

