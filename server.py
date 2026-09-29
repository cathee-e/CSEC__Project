import socket

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