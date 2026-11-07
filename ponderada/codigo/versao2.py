"""Versão 2 da A4: buffer circular protegido por semáforos.

O produtor espera por uma posição vazia antes de entrar na região crítica. O
consumidor espera por uma posição cheia. Execute este arquivo com Python 3
a partir da raiz do repositório.
"""

from __future__ import annotations

import threading
import time
from collections import Counter


N = 5
TOTAL_SAMPLES = 20_000
IDLE_TIMEOUT_SECONDS = 1.0


def run_once(sample_count: int = TOTAL_SAMPLES, buffer_size: int = N) -> dict[str, int | bool]:
    """Execute uma rodada com semáforos vazio, cheio e mutex.

    Args:
        sample_count: Quantidade de identificadores que o produtor gera.
        buffer_size: Quantidade de posições do buffer circular.

    Returns:
        Um resumo com amostras consumidas, perdidas, duplicadas e travamento.

    Funcionamento:
        ``empty`` conta posições livres, ``full`` conta amostras disponíveis e
        ``mutex`` protege o buffer e os índices. A ordem do produtor é P(empty)
        seguida de P(mutex), evitando segurar o mutex enquanto não há espaço.
    """
    buffer: list[int | None] = [None] * buffer_size
    empty = threading.Semaphore(buffer_size)
    full = threading.Semaphore(0)
    mutex = threading.Semaphore(1)
    write_index = 0
    read_index = 0
    consumed: list[int] = []
    producer_done = threading.Event()
    stop = threading.Event()
    status: dict[str, bool] = {"timed_out": False}

    def producer() -> None:
        """Espere por espaço, escreva uma amostra e sinalize full.

        Parâmetros: nenhum. Retorno: None.
        Funcionamento: executa P(empty), entra no mutex, grava o ID e sinaliza
        full depois de sair da região crítica.
        """
        nonlocal write_index
        try:
            for sample_id in range(sample_count):
                while not stop.is_set():
                    if empty.acquire(timeout=0.1):
                        break
                else:
                    return
                if stop.is_set():
                    empty.release()
                    return
                mutex.acquire()
                try:
                    buffer[write_index] = sample_id
                    write_index = (write_index + 1) % buffer_size
                finally:
                    mutex.release()
                full.release()
        finally:
            producer_done.set()

    def consumer() -> None:
        """Espere por uma amostra, leia-a e sinalize empty.

        Parâmetros: nenhum. Retorno: None.
        Funcionamento: executa P(full), lê e limpa uma posição sob mutex e
        sinaliza empty após sair da região crítica.
        """
        nonlocal read_index
        last_received = time.monotonic()
        while not stop.is_set():
            if not full.acquire(timeout=IDLE_TIMEOUT_SECONDS):
                if producer_done.is_set():
                    break
                if time.monotonic() - last_received >= IDLE_TIMEOUT_SECONDS:
                    status["timed_out"] = True
                    stop.set()
                    break
                continue
            mutex.acquire()
            try:
                sample_id = buffer[read_index]
                buffer[read_index] = None
                read_index = (read_index + 1) % buffer_size
            finally:
                mutex.release()
            empty.release()
            if sample_id is not None:
                consumed.append(sample_id)
                last_received = time.monotonic()

    consumer_thread = threading.Thread(target=consumer, name="motor", daemon=True)
    producer_thread = threading.Thread(target=producer, name="sensor", daemon=True)
    consumer_thread.start()
    producer_thread.start()
    producer_thread.join(IDLE_TIMEOUT_SECONDS + 2.0)
    consumer_thread.join(IDLE_TIMEOUT_SECONDS + 2.0)
    hung = bool(status["timed_out"]) or consumer_thread.is_alive() or producer_thread.is_alive()
    if hung:
        stop.set()

    frequencies = Counter(consumed)
    unique_received = sum(1 for sample_id in frequencies if 0 <= sample_id < sample_count)
    duplicate_count = sum(max(0, count - 1) for sample_id, count in frequencies.items() if 0 <= sample_id < sample_count)
    return {
        "consumed": len(consumed),
        "lost": sample_count - unique_received,
        "duplicated": duplicate_count,
        "hung": hung,
    }


def main() -> None:
    """Execute uma rodada e imprima uma linha de resultados.

    Parâmetros: nenhum. Retorno: None.
    Funcionamento: chama run_once com os valores padrão e formata o resumo.
    """
    result = run_once()
    print("Versao 2 | semaforos na ordem segura | N=5 | amostras=20.000")
    print("consumidas={consumed} perdidas={lost} duplicadas={duplicated} travou={hung}".format(**result))


if __name__ == "__main__":
    main()
