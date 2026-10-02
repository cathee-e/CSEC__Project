# crypto_module.py - Caesar, RSA and AES for the RFMP project
import random
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


# ---------------- CAESAR ----------------
def caesar_encrypt(text, shift):
    # Shift each letter forward by 'shift', wrapping around the alphabet.
    # Other characters (digits, spaces, commas) are left unchanged.
    result = ""
    for ch in text:
        if ch >= "A" and ch <= "Z":
            result = result + chr((ord(ch) - ord("A") + shift) % 26 + ord("A"))
        elif ch >= "a" and ch <= "z":
            result = result + chr((ord(ch) - ord("a") + shift) % 26 + ord("a"))
        else:
            result = result + ch
    return result


def caesar_decrypt(text, shift):
    # Decrypting is shifting backwards
    return caesar_encrypt(text, -shift)


# ---------------- RSA ----------------
def is_prime(n):
    # A number is prime if nothing from 2 up to its square root divides it
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True


def gcd(a, b):
    # Euclid's algorithm: greatest common divisor
    while b != 0:
        a, b = b, a % b
    return a


def rsa_generate_keypair():
    # Returns (public, private) as strings "e-n" and "d-n"
    primes = []
    for x in range(100, 1000):
        if is_prime(x):
            primes.append(x)

    p = random.choice(primes)
    q = random.choice(primes)
    while q == p:                       # p and q must be different
        q = random.choice(primes)

    n = p * q
    phi = (p - 1) * (q - 1)

    e = 17                              # e must share no factor with phi
    while gcd(e, phi) != 1:
        e = e + 2

    d = 1                               # d is where (e * d) % phi == 1
    while (e * d) % phi != 1:
        d = d + 1

    return (str(e) + "-" + str(n), str(d) + "-" + str(n))


def rsa_encrypt(text, pub):
    # Encrypt each character: (character number ** e) % n
    parts = pub.split("-")
    e = int(parts[0])
    n = int(parts[1])
    numbers = []
    for ch in text:
        numbers.append(str(pow(ord(ch), e, n)))   # pow(a, b, n) = (a ** b) % n
    return ".".join(numbers)            # dots, because commas would break the packet


def rsa_decrypt(data, priv):
    # Decrypt each number: (number ** d) % n, then turn it back into a character
    parts = priv.split("-")
    d = int(parts[0])
    n = int(parts[1])
    text = ""
    for num in data.split("."):
        text = text + chr(pow(int(num), d, n))
    return text


# ---------------- AES ----------------
def aes_encrypt(text, key):
    # AES-128 in CBC mode. The key is the 16-character session key.
    iv = get_random_bytes(16)                         # random starting block
    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv)
    padded = pad(text.encode("utf-8"), 16)            # pad to a multiple of 16 bytes
    ciphertext = cipher.encrypt(padded)
    return (iv + ciphertext).hex()                    # hex has no commas or brackets


def aes_decrypt(data, key):
    raw = bytes.fromhex(data)                         # hex text back to bytes
    iv = raw[:16]                                     # first 16 bytes are the IV
    ciphertext = raw[16:]
    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv)
    padded = cipher.decrypt(ciphertext)
    return unpad(padded, 16).decode("utf-8")          # remove the padding


# ---------------- SESSION KEY AND DISPATCHERS ----------------
def generate_session_key(alg):
    if alg == "CAESAR":
        return str(random.randint(1, 25))             # a shift, sent as text
    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    key = ""
    for i in range(16):                               # 16 characters = AES-128 key
        key = key + random.choice(letters)
    return key


def encrypt(text, alg, key):
    if alg == "AES":
        return aes_encrypt(text, key)
    return caesar_encrypt(text, int(key))


def decrypt(data, alg, key):
    if alg == "AES":
        return aes_decrypt(data, key)
    return caesar_decrypt(data, int(key))


# ---------------- SELF-TEST ----------------
if __name__ == "__main__":
    for alg in ["CAESAR", "AES"]:
        k = generate_session_key(alg)
        secret = encrypt("Hello, World", alg, k)
        print(alg, "key:", k, "encrypted:", secret)
        assert decrypt(secret, alg, k) == "Hello, World"

    pub, priv = rsa_generate_keypair()
    sk = generate_session_key("AES")
    assert rsa_decrypt(rsa_encrypt(sk, pub), priv) == sk
    print("RSA public key:", pub)
    print("All tests passed")