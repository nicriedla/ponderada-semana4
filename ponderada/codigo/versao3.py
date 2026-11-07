"""Versão 3 da A4: ordem de espera do produtor propensa a deadlock.

O produtor adquire ``mutex`` antes de esperar por ``empty``. O ensaio enche o
buffer e alinha as threads para tornar o deadlock reproduzível. Execute este
arquivo com Python 3 a partir da raiz do repositório.
"""

from __future__ import annotations

import threading
from collections import Counter


N = 5
TOTAL_SAMPLES = 20_000
DEADLOCK_OBSERVATION_SECONDS = 1.0


def run_once(sample_count: int = TOTAL_SAMPLES, buffer_size: int = N) -> dict[str, int | bool]:
    """Reproduza o deadlock causado pela ordem invertida no produtor.

    Args:
        sample_count: Quantidade de identificadores que o produtor tentaria gerar.
        buffer_size: Quantidade de posições do buffer circular.

    Returns:
        Um resumo com amostras consumidas, perdidas, duplicadas e travamento.

    Funcionamento:
        Após encher o buffer, o produtor segura ``mutex`` enquanto espera
        ``empty``. A thread do motor consome um token de ``full`` e passa a
        esperar pelo mesmo mutex. Threads daemon permitem encerrar o ensaio após
        um segundo sem transferir uma amostra.
    """
    buffer: list[int | None] = [None] * buffer_size
    empty = threading.Semaphore(buffer_size)
    full = threading.Semaphore(0)
    mutex = threading.Semaphore(1)
    write_index = 0
    read_index = 0
    consumed: list[int] = []
    producer_holds_mutex_on_full_buffer = threading.Event()
    status: dict[str, bool] = {"timed_out": False}

    def producer() -> None:
        """Adquira mutex antes de espaço e bloqueie quando o buffer encher.

        Parâmetros: nenhum. Retorno: None.
        Funcionamento: executa P(mutex) seguido de P(empty); com o buffer
        cheio, fica bloqueado enquanto ainda mantém mutex.
        """
        nonlocal write_index
        for sample_id in range(sample_count):
            mutex.acquire()
            if sample_id == buffer_size:
                producer_holds_mutex_on_full_buffer.set()
            empty.acquire()
            try:
                buffer[write_index] = sample_id
                write_index = (write_index + 1) % buffer_size
            finally:
                mutex.release()
            full.release()

    def consumer() -> None:
        """Aguarde o buffer cheio e tente adquirir o mutex do produtor.

        Parâmetros: nenhum. Retorno: None.
        Funcionamento: sincroniza o ensaio para o buffer cheio, executa
        P(full) e tenta P(mutex), marcando o timeout do deadlock.
        """
        nonlocal read_index
        if not producer_holds_mutex_on_full_buffer.wait(DEADLOCK_OBSERVATION_SECONDS + 1.0):
            status["timed_out"] = True
            return
        if not full.acquire(timeout=DEADLOCK_OBSERVATION_SECONDS):
            status["timed_out"] = True
            return
        if not mutex.acquire(timeout=DEADLOCK_OBSERVATION_SECONDS):
            status["timed_out"] = True
            return
        try:
            sample_id = buffer[read_index]
            read_index = (read_index + 1) % buffer_size
            if sample_id is not None:
                consumed.append(sample_id)
        finally:
            mutex.release()
        empty.release()

    producer_thread = threading.Thread(target=producer, name="sensor", daemon=True)
    consumer_thread = threading.Thread(target=consumer, name="motor", daemon=True)
    producer_thread.start()
    consumer_thread.start()
    producer_thread.join(DEADLOCK_OBSERVATION_SECONDS + 0.5)
    consumer_thread.join(DEADLOCK_OBSERVATION_SECONDS + 0.5)
    hung = bool(status["timed_out"]) or producer_thread.is_alive() or consumer_thread.is_alive()

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
    print("Versao 3 | produtor espera mutex antes de vazio | N=5 | amostras=20.000")
    print("consumidas={consumed} perdidas={lost} duplicadas={duplicated} travou={hung}".format(**result))


if __name__ == "__main__":
    main()
