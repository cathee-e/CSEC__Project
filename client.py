import socket

#It loops over the fields, adds a comma between them, wraps them in brackets, and sends the encoded string.
def send_packet(s, fields): # Build a packet string from a list, e.g. ["CM", "prompt", "ls"] -> "(CM,prompt,ls)", then send it.
    packet = "("
    for i in range(len(fields)):
        if i > 0:
            packet = packet + ","            # comma between fields
        packet = packet + str(fields[i])     # str() so numbers like 0 also work
    packet = packet + ")"
    s.send(packet.encode("utf-8"))          