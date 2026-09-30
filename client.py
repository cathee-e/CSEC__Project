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

def split_packet(msg, max_fields):
    # Split msg at commas into a list, but make at most max_fields pieces.
    # The last piece keeps any extra commas, so file text like "hello, world" is not broken apart.
    fields = []
    current = ""
    for ch in msg:                           # look at the text one character at a time
        if ch == "," and len(fields) < max_fields - 1:
            fields.append(current)           # finished one field
            current = ""
        else:
            current = current + ch           # keep building the current field
    fields.append(current)                   # the last field
    return fields

print(split_packet("SS,hello, world", 3))     