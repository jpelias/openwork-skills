#!/usr/bin/env python3
# scripts/extract_proto.py — Decodificación black-box de mensajes protobuf
# Sin esquema: interpreta wire types según la espec protobuf

import sys
import struct

def decode_varint(data, offset):
    result = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7f) << shift
        if not (byte & 0x80):
            return result, offset
        shift += 7
    raise ValueError("Truncated varint")

def decode_field(data, offset):
    tag, offset = decode_varint(data, offset)
    field_number = tag >> 3
    wire_type = tag & 0x07
    
    if wire_type == 0:  # varint
        value, offset = decode_varint(data, offset)
        print(f"  [{field_number}] varint: {value} (0x{value:x})")
    elif wire_type == 1:  # 64-bit
        value = struct.unpack_from('<Q', data, offset)[0]
        double_val = struct.unpack_from('<d', data, offset)[0]
        print(f"  [{field_number}] 64-bit: {double_val} (double)  / 0x{value:016x}")
        offset += 8
    elif wire_type == 2:  # length-delimited
        length, offset = decode_varint(data, offset)
        raw = data[offset:offset+length]
        # Try as UTF-8 string
        try:
            as_string = raw.decode('utf-8')
            if all(c.isprintable() or c in ('\n','\r','\t') for c in as_string):
                print(f"  [{field_number}] string: \"{as_string}\"")
            else:
                print(f"  [{field_number}] bytes[{length}]: {raw.hex()}")
        except UnicodeDecodeError:
            print(f"  [{field_number}] bytes[{length}]: {raw.hex()}")
        offset += length
    elif wire_type == 5:  # 32-bit
        value = struct.unpack_from('<I', data, offset)[0]
        float_val = struct.unpack_from('<f', data, offset)[0]
        print(f"  [{field_number}] 32-bit: {float_val} (float) / 0x{value:08x}")
        offset += 4
    elif wire_type == 3 or wire_type == 4:
        # Start/end group (deprecated)
        print(f"  [{field_number}] GROUP start/end (deprecated, wire_type={wire_type})")
    else:
        print(f"  [{field_number}] UNKNOWN wire_type={wire_type}")
    
    return offset

def parse_protobuf(data):
    offset = 0
    while offset < len(data):
        try:
            next_off = decode_field(data, offset)
            if next_off == offset:
                break
            offset = next_off
        except Exception as e:
            print(f"  [ERROR @ {offset}] {e}")
            print(f"  Remaining bytes: {data[offset:offset+32].hex()}")
            break

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Uso: {sys.argv[0]} <archivo.bin>")
        print("  Si el frame es gRPC, saltar los primeros 5 bytes: tail -c +6 request.bin | python3 extract_proto.py /dev/stdin")
        sys.exit(1)
    
    path = sys.argv[1]
    if path == '/dev/stdin':
        data = sys.stdin.buffer.read()
    else:
        with open(path, 'rb') as f:
            data = f.read()
    
    print(f"=== Protobuf black-box decode ({len(data)} bytes) ===")
    parse_protobuf(data)
