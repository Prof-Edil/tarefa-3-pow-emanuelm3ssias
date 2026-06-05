#!/usr/bin/env python3
"""
Exercicio 1 — Selecao de Transacoes do Mempool
================================================
"""

import csv
import sys
from pathlib import Path

# ─── Configuracoes

BASE          = Path(__file__).parent.parent
MEMPOOL_PATH  = BASE / "data" / "mempool.csv"
OUTPUT_PATH   = BASE / "solutions" / "exercise01.txt"

REQUIRED_TXID = "4c50e3dad7f98bceb6441f96b23748dea84fbdb7cedd603441e6ea4a574d04a6"
WEIGHT_LIMIT  = 4_000_000
MIN_FEE       = 50_000


# ─── Carregamento do mempool

def load_mempool(path: Path) -> dict:
    """Le o CSV do mempool e retorna um dicionario {txid: {fee, weight, parents}}."""
    mempool = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 3:
                continue
            txid   = row[0].strip().lower()
            fee    = int(row[1])
            weight = int(row[2])
            parents_raw = row[3].strip() if len(row) >= 4 else ""
            parents = (
                [p.strip().lower() for p in parents_raw.split(";") if p.strip()]
                if parents_raw else []
            )
            mempool[txid] = {"fee": fee, "weight": weight, "parents": parents}
    return mempool


# ─── Ordenacao topologica

def topological_sort(mempool: dict) -> list:
    """Retorna txids em ordem topologica (pais antes dos filhos)."""
    visited, result = set(), []

    def dfs(txid):
        if txid in visited:
            return
        if txid not in mempool:
            return
        visited.add(txid)
        for p in mempool[txid]["parents"]:
            dfs(p)
        result.append(txid)

    for txid in list(mempool.keys()):
        dfs(txid)
    return result


# ─── Coleta de ancestrais

def get_all_ancestors(txid: str, mempool: dict, memo: dict = None) -> set:
    """Retorna todos os ancestrais (recursivos) de uma tx que estao no mempool."""
    if memo is None:
        memo = {}
    if txid in memo:
        return memo[txid]
    anc = set()
    for p in mempool.get(txid, {}).get("parents", []):
        if p in mempool:
            anc.add(p)
            anc |= get_all_ancestors(p, mempool, memo)
    memo[txid] = anc
    return anc


# ─── Selecao do bloco

def select_block(mempool: dict, ordered: list) -> list:
    """
    Seleciona transacoes para o bloco seguindo a estrategia:
    1. Inclui forcosamente a tx obrigatoria e todos os seus ancestrais.
    2. Greedy topologico: adiciona qualquer tx que caiba no peso restante.
    """
    included     = set()
    block        = []
    total_weight = 0
    total_fee    = 0

    def try_add(txid):
        nonlocal total_weight, total_fee
        if txid in included:
            return
        tx = mempool[txid]
        if total_weight + tx["weight"] <= WEIGHT_LIMIT:
            included.add(txid)
            block.append(txid)
            total_weight += tx["weight"]
            total_fee    += tx["fee"]

    def can_include(txid):
        """Todos os pais que estao no mempool ja foram incluidos."""
        return all(
            p not in mempool or p in included
            for p in mempool[txid]["parents"]
        )

    # Passo 1: tx obrigatoria e seus ancestrais (em ordem topologica)
    req_ancestors = get_all_ancestors(REQUIRED_TXID, mempool)
    for txid in ordered:
        if txid in req_ancestors:
            try_add(txid)

    if can_include(REQUIRED_TXID):
        try_add(REQUIRED_TXID)

    # Passo 2: greedy por ordem topologica
    changed = True
    while changed:
        changed = False
        for txid in ordered:
            if txid in included:
                continue
            if not can_include(txid):
                continue
            before = total_weight
            try_add(txid)
            if total_weight != before:
                changed = True

    return block, total_weight, total_fee


# ─── Main

def main():
    print("Carregando mempool...")
    mempool = load_mempool(MEMPOOL_PATH)
    print("  {} transacoes encontradas".format(len(mempool)))

    print("Ordenando topologicamente...")
    ordered = topological_sort(mempool)

    print("Selecionando bloco...")
    block, total_weight, total_fee = select_block(mempool, ordered)

    # Validacoes
    ok = True
    if REQUIRED_TXID not in set(block):
        print("ERRO: transacao obrigatoria nao incluida!")
        ok = False
    if total_weight > WEIGHT_LIMIT:
        print("ERRO: peso excede o limite ({} > {})".format(total_weight, WEIGHT_LIMIT))
        ok = False
    if total_fee < MIN_FEE:
        print("AVISO: fee minima nao atingida ({} < {})".format(total_fee, MIN_FEE))
        ok = False

    print("")
    print("Resultado:")
    print("  Transacoes  : {}".format(len(block)))
    print("  Peso total  : {:,} / {:,}".format(total_weight, WEIGHT_LIMIT))
    print("  Fees totais : {:,} sats".format(total_fee))
    print("  Valido      : {}".format(ok))

    if not ok:
        sys.exit(1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write("\n".join(block) + "\n")
    print("  Salvo em    : {}".format(OUTPUT_PATH))


if __name__ == "__main__":
    main()