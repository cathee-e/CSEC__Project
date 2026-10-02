// client.c - RFMP C client (non-secure, openRead only) for Windows
// Stage 1: create a socket and connect to the server
#include <stdio.h>
#include <string.h>
#include <winsock2.h>
#include <ws2tcpip.h>

#define PORT "8888"

int main() {
    WSADATA wsa;
    SOCKET s;
    struct addrinfo hints, *result;
    struct sockaddr_in *addr;
    char host[256];

    // Start Winsock (needed on Windows before using sockets)
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        printf("Winsock failed to start\n");
        return 1;
    }

    // Look up this computer's name the same way the Python server does (IPv4, TCP)
    gethostname(host, sizeof(host));
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    if (getaddrinfo(host, PORT, &hints, &result) != 0) {
        printf("Could not find the server host\n");
        WSACleanup();
        return 1;
    }

    addr = (struct sockaddr_in *)result->ai_addr;
    printf("Trying %s on port %s\n", inet_ntoa(addr->sin_addr), PORT);

    // Create a TCP socket
    s = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
    if (s == INVALID_SOCKET) {
        printf("Could not create socket\n");
        WSACleanup();
        return 1;
    }

    // Connect to the server
    if (connect(s, result->ai_addr, (int)result->ai_addrlen) == SOCKET_ERROR) {
        printf("Could not connect (error %d). Is the server running?\n", WSAGetLastError());
        closesocket(s);
        WSACleanup();
        return 1;
    }
    printf("Connected to the server\n");

    freeaddrinfo(result);
    closesocket(s);
    WSACleanup();
    return 0;
}