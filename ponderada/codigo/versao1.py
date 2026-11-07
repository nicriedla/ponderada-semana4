"""Versão 1 da A4: buffer circular sem sincronização.

O contador de posições ocupadas é compartilhado sem mutex. time.sleep(0)
cede a execução entre a leitura e a escrita do contador para expor atualizações
perdidas. Execute com Python 3: python3 ponderada/codigo/versao1.py.
"""

from __future__ import annotations

import threading
import time
from collections import Counter


N = 5
TOTAL_SAMPLES = 20_000
IDLE_TIMEOUT_SECONDS = 1.0


def run_once(sample_count: int = TOTAL_SAMPLES, buffer_size: int = N) -> dict[str, int | bool]:
    """Execute uma rodada do produtor e consumidor sem sincronização.

    Args:
        sample_count: Quantidade de identificadores que o produtor tenta gerar.
        buffer_size: Quantidade de posições do buffer circular.

    Returns:
        Um resumo com amostras consumidas, perdidas, duplicadas e travamento.

    Funcionamento:
        Duas threads compartilham o buffer e o contador ``occupied``. A pausa
        ``time.sleep(0)`` entre ler e atualizar esse contador permite que a outra
        thread sobrescreva uma atualização. O consumidor encerra se ficar um
        segundo sem receber uma amostra válida.
    """
    buffer: list[int | None] = [None] * buffer_size
    occupied = 0
    write_index = 0
    read_index = 0
    consumed: list[int] = []
    producer_done = threading.Event()
    stop = threading.Event()
    status: dict[str, int | bool] = {"timed_out": False, "invalid_reads": 0}

    def producer() -> None:
        """Produza IDs e atualize o contador compartilhado sem proteção.

        Parâmetros: nenhum. Retorno: None.
        Funcionamento: grava cada ID no buffer e altera occupied sem mutex,
        cedendo a execução entre ler e escrever o contador.
        """
        nonlocal occupied, write_index
        try:
            for sample_id in range(sample_count):
                while not stop.is_set():
                    observed_occupied = occupied
                    if observed_occupied < buffer_size:
                        time.sleep(0)
                        buffer[write_index] = sample_id
                        write_index = (write_index + 1) % buffer_size
                        occupied = observed_occupied + 1
                        break
                    time.sleep(0)
                if stop.is_set():
                    break
        finally:
            producer_done.set()

    def consumer() -> None:
        """Consuma IDs e encerre após um segundo sem amostra válida.

        Parâmetros: nenhum. Retorno: None.
        Funcionamento: lê do buffer, altera occupied sem mutex e registra os
        IDs recebidos; encerra ao detectar o limite de inatividade.
        """
        nonlocal occupied, read_index
        last_received = time.monotonic()
        while not stop.is_set():
            observed_occupied = occupied
            if observed_occupied > 0:
                sample_id = buffer[read_index]
                read_index = (read_index + 1) % buffer_size
                time.sleep(0)
                occupied = observed_occupied - 1
                if sample_id is None:
                    status["invalid_reads"] = int(status["invalid_reads"]) + 1
                else:
                    consumed.append(sample_id)
                    last_received = time.monotonic()
            elif producer_done.is_set():
                break
            elif time.monotonic() - last_received >= IDLE_TIMEOUT_SECONDS:
                status["timed_out"] = True
                stop.set()
                break
            else:
                time.sleep(0)

    consumer_thread = threading.Thread(target=consumer, name="motor", daemon=True)
    producer_thread = threading.Thread(target=producer, name="sensor", daemon=True)
    consumer_thread.start()
    producer_thread.start()
    consumer_thread.join(IDLE_TIMEOUT_SECONDS + 2.0)
    producer_thread.join(IDLE_TIMEOUT_SECONDS + 2.0)
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
    print("Versao 1 | sem sincronizacao | N=5 | amostras=20.000")
    print("consumidas={consumed} perdidas={lost} duplicadas={duplicated} travou={hung}".format(**result))


if __name__ == "__main__":
    main()
