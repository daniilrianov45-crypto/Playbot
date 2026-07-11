"""Provably fair: результат каждой игры выводится из HMAC-SHA256(server_seed, client_seed:nonce:i).

До игры пользователь видит SHA-256 хэш server seed — сервер не может подменить
сид после ставок. После ротации сид раскрывается, и любой исход можно
пересчитать вручную и сверить.
"""
import hashlib
import hmac
import secrets


def new_server_seed() -> str:
    return secrets.token_hex(32)


def new_client_seed() -> str:
    return secrets.token_hex(8)


def seed_hash(server_seed: str) -> str:
    return hashlib.sha256(server_seed.encode()).hexdigest()


def roll_floats(server_seed: str, client_seed: str, nonce: int, count: int = 1) -> list[float]:
    """count равномерных чисел в [0, 1): по одному HMAC на число (52 бита каждое)."""
    out = []
    for i in range(count):
        msg = f"{client_seed}:{nonce}:{i}".encode()
        digest = hmac.new(server_seed.encode(), msg, hashlib.sha256).hexdigest()
        out.append(int(digest[:13], 16) / 2**52)
    return out
