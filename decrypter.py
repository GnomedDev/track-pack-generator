import struct
import sys
from io import BufferedReader, BufferedWriter

from Crypto.Cipher import AES

BLOB_KEY = bytes([0x90, 0x83, 0x00, 0x04, 0x90, 0xA3, 0x00, 0x08, 0x90, 0xC3, 0x00, 0x0C, 0x4E, 0x80, 0x00, 0x20])

def get_size(file: BufferedReader) -> int:
    file.seek(0, 2)
    size = file.tell()
    file.seek(0, 0)

    return size

def run(input: BufferedReader, output: BufferedWriter, encode: bool):
    input_size = get_size(input)

    i = 0
    while i < input_size / 512:
        data = []
        curIv = struct.pack(">IIII", 0x80630004, 0x90830004, i, 0x4E800020)
        cipher = AES.new(BLOB_KEY, AES.MODE_CBC, iv=curIv) # type: ignore
        if encode:
            data = cipher.encrypt(input.read(0x8000))
        else:
            data = cipher.decrypt(input.read(0x8000))

        output.write(data)
        i += 64

if __name__ == "__main__":
    encode = False
    if sys.argv[1] == "enc":
        encode = True
    elif sys.argv[1] == "dec":
        encode = False
    else:
        raise SystemExit("invalid encrypt mode!")

    infile = open(sys.argv[2], "rb")
    outfile = open(sys.argv[3], "wb")

    run(infile, outfile, encode)
