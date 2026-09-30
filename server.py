import socket
import threading

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

    # Check that this is a valid RFMP start packet
    if packet[0] == "SS" and packet[1] == "RFMP" and packet[2] == "v1.0":
        print("Valid RFMP start packet received")

        # Check whether secure communication was requested
        if packet[3] == "0":
            print("Non-secure communication requested")

            # Confirm the connection
            confirmation = "(CC)"
            client_socket.send(confirmation.encode("utf-8"))

            print("Sent:", confirmation)

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