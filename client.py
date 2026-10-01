import socket

#Part 3 will replace these with the real crypto module 
def encrypt(text, alg, key): 
    return text            # stub:returns the text unchanged
def decrypt(data, alg, key): 
    return data            # stub: returns the data unchanged
def rsa_generate_keypair(): 
    return ("1-1", "1-1")   # stub:encrypt the session key with the server's public key
def rsa_encrypt(text, pub): 
    return text             # returns the text unchanged
def generate_session_key(alg):                      # stub:Part 3 will make a real random key
    if alg == "CAESAR":
        return "5"
    return "0123456789abcdef"
#

#step 1: Builds and sends every packet (SS, EC, CM, DP, End).
#It loops over the fields, adds a comma between them, wraps them in brackets, and sends the encoded string.
def send_packet(s, fields): # Build a packet string from a list, e.g. ["CM", "prompt", "ls"] -> "(CM,prompt,ls)", then send it.
    packet = "("
    for i in range(len(fields)):
        if i > 0:
            packet = packet + ","            # comma between fields
        packet = packet + str(fields[i])     # str() so numbers like 0 also work
    packet = packet + ")"
    s.send(packet.encode("utf-8"))     

#step 2: recv_packet uses it to cut the text at the commas. 
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

#step3: Receives every server reply and turns it into fields.
def recv_packet(s):
    # Receive one packet and turn it into a list, e.g. "(EE,2,File not found)" -> ["EE", "2", "File not found"]
    msg = s.recv(2024).decode("utf-8")       # bytes -> string (as in TCPClientExample.py)
    msg = msg[1:len(msg) - 1]                # slicing removes the "(" at the start and ")" at the end
    if msg[0:2] == "EE":
        return split_packet(msg, 3)          # EE has 3 fields: type, code, description
    return split_packet(msg, 2)              # other packets: type + the rest

# Error codes (must match the server, maximum 4)
ERRORS = {1: "Unknown command",
          2: "File not found",
          3: "Invalid arguments / permission denied",
          4: "Protocol or crypto error"}

#step4: handling EE packets and error codes.
def check_response(fields):
    # Every server response goes through here. EE = the server had an error.
    # Returns True if the response is OK, False if it was an EE packet.
    if fields[0] == "EE":
        code = int(fields[1])                # the code arrives as text, so int() turns it into a number
        if code in ERRORS:
            name = ERRORS[code]              # look up the meaning of the code
        else:
            name = "Unknown error"
        print("[ERROR " + str(code) + "] " + name + " - " + fields[2])
        return False
    return True

#step 5: It sends SS and EC, which are part of the protocol.
def setup_phase(s, secure):
    # Setup phase: SS -> CC -> (EC if secure). Returns (algorithm, session_key), or ("", "") if not secure.
    if secure:
        send_packet(s, ["SS", "RFMP", "v1.0", 1])
    else:
        send_packet(s, ["SS", "RFMP", "v1.0", 0])
 
    cc = recv_packet(s)                      # the server must answer with CC
    if cc[0] != "CC":
        print("Expected CC packet, got:", cc)
        return "", ""
    if not secure:
        return "", ""
 
    server_public_key = cc[1]                # (CC,Server_public_key)
 
    alg = ""
    while alg != "AES" and alg != "CAESAR":  # input validation
        alg = input("Algorithm (type AES or CAESAR): ")
 
    session_key = generate_session_key(alg)              # made by the crypto module (Part 3)
    my_public, my_private = rsa_generate_keypair()       # the spec says the client also has an RSA pair
    encrypted_key = rsa_encrypt(session_key, server_public_key)  # only the server's private key can open it
    send_packet(s, ["EC", alg, encrypted_key, "user1:" + my_public])
    return alg, session_key
 
 
def run_prompt(s):
    # Operation phase: send a system command such as mkdir, cd, rmdir, del, ren
    cmd = input("Command (mkdir, cd, rmdir, del, ren, ...): ")
    send_packet(s, ["CM", "prompt", cmd])
    resp = recv_packet(s)
    if check_response(resp):
        if len(resp) > 1:
            print("Server:", resp[1])
        else:
            print("Server: done")
 
 
def open_read(s, alg, key):
    # openRead: ask the server for a file's contents (encrypted if secure)
    name = input("File name to read: ")
    send_packet(s, ["CM", "openRead", name])
    resp = recv_packet(s)
    if check_response(resp):
        data = resp[1]
        if alg != "":                      # secure mode: decrypt what the server sent
            data = decrypt(data, alg, key)
        print("----- file contents -----")
        print(data)
 
 
def open_write(s, alg, key):
    # openWrite: tell the server the file name, then send the text in a DP packet
    name = input("File name to write: ")
    send_packet(s, ["CM", "openWrite", name])
    if not check_response(recv_packet(s)):   # the server may refuse before we send any data
        return
    text = input("Text to save in the file: ")
    if alg != "":                          # secure mode: encrypt before sending
        text = encrypt(text, alg, key)
    send_packet(s, ["DP", text])
    if check_response(recv_packet(s)):
        print("File saved.")
 
 
def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostname()
    port = 8888
    s.connect((host, port))
 
    answer = input("Secure communication? (y/n): ")
    secure = (answer == "y")
    alg, key = setup_phase(s, secure)
 
    while True:                              # operation phase
        print("\n1) Run command   2) openRead   3) openWrite   4) Quit")
        choice = input("> ")
        if choice == "1":
            run_prompt(s)
        elif choice == "2":
            open_read(s, alg, key)
        elif choice == "3":
            open_write(s, alg, key)
        elif choice == "4":
            send_packet(s, ["End"])          # closing phase
            break
        else:
            print("Invalid choice")
 
    s.close()
 
 
if __name__ == '__main__':
    main()
 