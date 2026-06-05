#!/usr/bin/env python3
"""
Exercicio 3 — Proof of Work (Mineracao)
=========================================
"""

import hashlib
import multiprocessing
import time
import sys
from pathlib import Path

# ─── Configuracoes

BASE        = Path(__file__).parent.parent
OUTPUT_PATH = BASE / "solutions" / "exercise03.txt"

VERSION     = 2  # deve ser > 1
PREV_BLOCK  = "00000000d1145790a8694403d4063f323d499e655c83426834d4ce2f8dd4a2ee"

# Merkle root fixo exigido pelo grader (calculado no exercicio 2)
MERKLE_ROOT = "c0a692de10b69e2381a2856dcb0d0736dcd307bf25af7ce74831bf25793de626"

# Janela de timestamp valida (Unix time)
TIMESTAMP_MIN = 1230999305  # Jan 03 2009 16:15:05 UTC
TIMESTAMP_MAX = 1231723825  # Jan 12 2009 01:30:25 UTC

# Target: 0x1d00ffff (compact) -> valor inteiro de 256 bits
TARGET_INT = 0x00000000ffff0000000000000000000000000000000000000000000000000000


# ─── Hash

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


# ─── Construcao do header

def build_header(version: int, prev_block: str, merkle_root: str,
                 timestamp: int, nonce: int) -> bytes:
    """
    Serializa o header do bloco em big-endian.
    Total: 4 + 32 + 32 + 4 + 8 = 80 bytes.
    """
    return (
        version.to_bytes(4, "big")
        + bytes.fromhex(prev_block)
        + bytes.fromhex(merkle_root)
        + timestamp.to_bytes(4, "big")
        + nonce.to_bytes(8, "big")
    )


# ─── Worker de mineracao

def mine_range(args):
    """
    Testado em um processo separado.
    Recebe (version, prev_hex, merkle_hex, timestamp, nonce_start, nonce_end, target).
    Retorna (nonce, header_hex, hash_hex) se encontrar, ou None.
    """
    version, prev_hex, merkle_hex, timestamp, nonce_start, nonce_end, target = args

    # Prefixo fixo para nao recalcular a cada iteracao
    prefix = (
        version.to_bytes(4, "big")
        + bytes.fromhex(prev_hex)
        + bytes.fromhex(merkle_hex)
        + timestamp.to_bytes(4, "big")
    )

    for nonce in range(nonce_start, nonce_end):
        header   = prefix + nonce.to_bytes(8, "big")
        h        = hashlib.sha256(header).digest()
        hash_int = int.from_bytes(h, "big")
        if hash_int <= target:
            return (nonce, header.hex(), h.hex())
    return None


# ─── Mineracao paralela

def mine(version: int, prev_block: str, merkle_root: str,
         timestamp: int, target: int = TARGET_INT):
    """
    Minera o bloco usando todos os nucleos de CPU disponiveis.
    Retorna (nonce, header_hex, hash_hex).
    """
    num_cores   = multiprocessing.cpu_count()
    chunk_size  = 5_000_000   # 5M nonces por processo por rodada
    nonce_start = 0
    start_time  = time.time()

    print("  Nucleos CPU   : {}".format(num_cores))
    print("  Chunk size    : {:,}".format(chunk_size))
    print("  Minerando...")

    with multiprocessing.Pool(processes=num_cores) as pool:
        while True:
            # Cria chunks para cada processo
            chunks = [
                (version, prev_block, merkle_root, timestamp,
                 nonce_start + i * chunk_size,
                 nonce_start + (i + 1) * chunk_size,
                 target)
                for i in range(num_cores)
            ]

            results = pool.map(mine_range, chunks)

            for r in results:
                if r is not None:
                    return r

            nonce_start += num_cores * chunk_size
            elapsed = time.time() - start_time
            rate    = nonce_start / elapsed / 1e6 if elapsed > 0 else 0
            print("  {:>14,} nonces | {:>6.1f}s | {:>5.2f} MH/s".format(
                nonce_start, elapsed, rate), end="\r", flush=True)


# ─── Verificacao

def verify_header(header_hex: str) -> bool:
    """Verifica se o header satisfaz todos os requisitos do grader."""
    hdr      = bytes.fromhex(header_hex)
    ok       = True

    version   = int.from_bytes(hdr[0:4],  "big")
    prev      = hdr[4:36].hex()
    merkle    = hdr[36:68].hex()
    timestamp = int.from_bytes(hdr[68:72], "big")
    # nonce   = hdr[72:80]

    if version < 2:
        print("  FAIL: versao invalida ({})".format(version))
        ok = False
    if prev != PREV_BLOCK:
        print("  FAIL: prevhash incorreto")
        ok = False
    if merkle != MERKLE_ROOT:
        print("  FAIL: merkle root incorreto")
        ok = False
    if not (TIMESTAMP_MIN <= timestamp <= TIMESTAMP_MAX):
        print("  FAIL: timestamp fora do intervalo ({})".format(timestamp))
        ok = False

    block_hash = sha256(hdr)
    hash_int   = int.from_bytes(block_hash, "big")
    if hash_int > TARGET_INT:
        print("  FAIL: PoW insuficiente")
        print("  Hash  : {:064x}".format(hash_int))
        print("  Target: {:064x}".format(TARGET_INT))
        ok = False

    return ok


# ─── Main

def main():
    print("=== Exercicio 3: Proof of Work ===")
    print("  Versao      : {}".format(VERSION))
    print("  Prev Block  : {}".format(PREV_BLOCK))
    print("  Merkle Root : {}".format(MERKLE_ROOT))
    print("  Target      : {:064x}".format(TARGET_INT))
    print("  Timestamp   : {} - {}".format(TIMESTAMP_MIN, TIMESTAMP_MAX))

    # Usa o timestamp do meio da janela valida
    timestamp = (TIMESTAMP_MIN + TIMESTAMP_MAX) // 2

    start = time.time()
    nonce, header_hex, hash_hex = mine(VERSION, PREV_BLOCK, MERKLE_ROOT,
                                       timestamp, TARGET_INT)
    elapsed = time.time() - start

    print("\n")
    print("  Bloco encontrado!")
    print("  Nonce       : {}".format(nonce))
    print("  Hash        : {}".format(hash_hex))
    print("  Tempo       : {:.2f}s".format(elapsed))
    print("  Header      : {}...".format(header_hex[:32]))

    print("\nVerificando header...")
    if not verify_header(header_hex):
        print("ERRO: header invalido!")
        sys.exit(1)

    print("  OK: header valido!")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(header_hex + "\n")
    print("  Salvo em    : {}".format(OUTPUT_PATH))


if __name__ == "__main__":
    main()