#!/usr/bin/env python3
"""
Exercicio 2 — Merkle Root + Prova de Inclusao
"""

import hashlib
import sys
from pathlib import Path

# ─── Configuracoes

BASE           = Path(__file__).parent.parent
TXID_LIST_PATH = BASE / "data" / "ex02_txid_list.txt"
OUTPUT_PATH    = BASE / "solutions" / "exercise02.txt"

TARGET_TXID = "49ff8cccf1ca12179e9ae7a4760f550b5a18401b27e1e057604e27c3e10c08fb"


# ─── Hash

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


# ─── Merkle Root + Prova

def compute_merkle_root_and_proof(txids: list, target_txid: str):
    """
    Constroi a arvore de Merkle e retorna (root_hex, proof).

    proof e uma lista de hashes hex dos siblings, do nivel folha ate a raiz.
    Para verificar: combinar target com cada sibling em sequencia e chegar na root.
    """
    if target_txid not in txids:
        raise ValueError("Target txid nao encontrado na lista: {}".format(target_txid))

    # Nivel inicial: bytes de cada txid (big-endian)
    level      = [bytes.fromhex(tx) for tx in txids]
    target_idx = txids.index(target_txid)
    proof      = []
    idx        = target_idx

    while len(level) > 1:
        # Duplica o ultimo elemento se o nivel for impar
        if len(level) % 2 == 1:
            level.append(level[-1])

        # Sibling do elemento na posicao idx
        if idx % 2 == 0:
            sibling = level[idx + 1]
        else:
            sibling = level[idx - 1]
        proof.append(sibling.hex())

        # Sobe um nivel
        next_level = []
        for i in range(0, len(level), 2):
            next_level.append(sha256(level[i] + level[i + 1]))

        idx   = idx // 2
        level = next_level

    root = level[0].hex()
    return root, proof


# ─── Verificacao da prova

def verify_proof(target_txid: str, proof: list, expected_root: str,
                 target_idx: int, n_leaves: int) -> bool:
    """Verifica se a prova de inclusao leva corretamente a raiz."""
    current    = bytes.fromhex(target_txid)
    idx        = target_idx
    level_size = n_leaves

    for sibling_hex in proof:
        if level_size % 2 == 1:
            level_size += 1  # nivel foi expandido com duplicata
        sibling = bytes.fromhex(sibling_hex)
        if idx % 2 == 0:
            combined = current + sibling
        else:
            combined = sibling + current
        current    = sha256(combined)
        idx        = idx // 2
        level_size = level_size // 2

    return current.hex() == expected_root


# ─── Main

def main():
    print("Carregando lista de txids...")
    txids = []
    with open(TXID_LIST_PATH, encoding="utf-8") as f:
        for line in f:
            tx = line.strip().lower()
            if tx:
                txids.append(tx)
    print("  {} txids carregados".format(len(txids)))

    if TARGET_TXID not in txids:
        print("ERRO: target txid nao encontrado na lista!")
        sys.exit(1)

    target_idx = txids.index(TARGET_TXID)
    print("  Target txid na posicao {}".format(target_idx))

    print("Calculando Merkle Root e prova de inclusao...")
    root, proof = compute_merkle_root_and_proof(txids, TARGET_TXID)

    print("Verificando prova...")
    valid = verify_proof(TARGET_TXID, proof, root, target_idx, len(txids))

    print("")
    print("Resultado:")
    print("  Merkle Root : {}".format(root))
    print("  Profundidade: {} niveis".format(len(proof)))
    print("  Prova valida: {}".format(valid))

    if not valid:
        print("ERRO: prova de inclusao invalida!")
        sys.exit(1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(root + "\n")
        for sibling in proof:
            f.write(sibling + "\n")
    print("  Salvo em    : {}".format(OUTPUT_PATH))


if __name__ == "__main__":
    main()