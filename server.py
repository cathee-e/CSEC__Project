import socket
import threading
import subprocess

def send_error(client_socket, error_code, description):
    error_packet = "(EE," + error_code + "," + description + ")"
    client_socket.send(error_packet.encode("utf-8"))
    print("Sent:", error_packet)

def handle_client(client_socket, address):
    print("Handling client:", address)

    # Receive the start packet from the client
    data = client_socket.recv(1024)

    # Convert bytes into a string
    message = data.decode("utf-8")

    print("Received:", message)

    # Separate the packet into its fields
    packet = message.strip("()").split(",")

    print("Packet fields:", packet)

    # Check that the start packet has exactly four fields
    if len(packet) != 4:
      send_error(client_socket, "EE01", "Invalid packet")
      client_socket.close()
      return

    # Check that this is a valid RFMP start packet
    if packet[0] != "SS" or packet[1] != "RFMP" or packet[2] != "v1.0":
      send_error(client_socket, "EE01", "Invalid start packet")
      client_socket.close()
      return

    print("Valid RFMP start packet received")

    secure_mode = packet[3]

    if secure_mode == "0":
     print("Non-secure communication requested")

     confirmation = "(CC)"
     client_socket.send(confirmation.encode("utf-8"))

     print("Sent:", confirmation)

    elif secure_mode == "1":
     print("Secure communication requested")
     print("Secure setup will be integrated with the crypto module")

    else:
     send_error(client_socket, "EE01", "Invalid security option")
     client_socket.close()
     return

    # Operation phase
    while True:
        data = client_socket.recv(1024)

        # Client disconnected
        if not data:
            print("Client disconnected:", address)
            break

        message = data.decode("utf-8")
        print("Received:", message)

        # Closing phase
        if message == "(End)":
            print("Client ended the connection:", address)
            break

        # Parse command packet
        command_packet = message.strip("()").split(",", 2)

        if len(command_packet) != 3:
            send_error(client_socket, "EE01", "Invalid packet")
            continue

        packet_type = command_packet[0]
        command_type = command_packet[1]
        arguments = command_packet[2]

        if packet_type != "CM":
            send_error(client_socket, "EE01", "Invalid packet type")
            continue

        if command_type == "prompt":
            print("Executing command:", arguments)

            try:
                result = subprocess.run(
                    arguments,
                    shell=True,
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    success_packet = "(SC)"
                    client_socket.send(success_packet.encode("utf-8"))
                    print("Sent:", success_packet)

                else:
                    send_error(
                        client_socket,
                        "EE04",
                        "Operation failed"
                    )

            except Exception:
                send_error(
                    client_socket,
                    "EE04",
                    "Operation failed"
                )

    client_socket.close()
    print("Connection closed:", address)
    


# Create the server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Get the name of this computer
host = socket.gethostname()

# Port number the server will listen on
port = 8888

# Connect the socket to the host and port
server_socket.bind((host, port))

# Start listening for clients
server_socket.listen(5)

print("Server is listening on port " + str(port))

while True:
    # Wait for a client to connect
    client_socket, address = server_socket.accept()

    print("Client connected:", address)

    # Create a separate thread for this client
    client_thread = threading.Thread(
        target=handle_client,
        args=(client_socket, address)
    )

    # Start the thread
    client_thread.start()