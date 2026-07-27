"""
Manipulação de intervalos de tempo — pura, sem tocar no banco.

Usado pelo selector de disponibilidade pra combinar janelas de trabalho,
bloqueios (EmployeeTimeOff) e agendamentos já existentes (Scheduling) e
gerar os slots livres. Fica separado do selector pra ser testável sem
precisar de banco/Django rodando.
"""
from datetime import datetime, timedelta
from typing import List, NamedTuple


class Interval(NamedTuple):
    """
    Par (start, end) com campos nomeados — em vez de tupla anônima —
    pra que o schema de resposta (AvailabilitySlotOut) consiga ler
    `.start`/`.end` via atributo diretamente, sem precisar de conversão
    manual no meio do caminho.
    """
    start: datetime
    end: datetime


def subtract_intervals(free: List[Interval], blocked: List[Interval]) -> List[Interval]:
    """
    Subtrai os intervalos bloqueados dos livres.

    Cada bloqueio pode fragmentar um intervalo livre em dois menores
    (quando cai no meio), encolher uma das pontas, ou eliminar o
    intervalo inteiro (quando o bloqueio cobre tudo). Bloqueios que só
    encostam na borda (ex: livre 08h-12h, bloqueio 12h-13h) não tiram
    nada — são adjacentes, não sobrepostos.
    """
    result = list(free)
    for b_start, b_end in blocked:
        next_result = []
        for f_start, f_end in result:
            if b_end <= f_start or b_start >= f_end:
                # Bloqueio não toca esse intervalo (ou só encosta na borda)
                next_result.append(Interval(f_start, f_end))
                continue
            if b_start > f_start:
                next_result.append(Interval(f_start, min(b_start, f_end)))
            if b_end < f_end:
                next_result.append(Interval(max(b_end, f_start), f_end))
        result = next_result
    return [Interval(s, e) for s, e in result if s < e]


def slice_into_slots(free: List[Interval], slot_duration: timedelta) -> List[Interval]:
    """
    Fatia os intervalos livres em slots consecutivos do tamanho do
    serviço (slot dinâmico — não fixo em 15/30min). Slots não se
    sobrepõem: cada um começa exatamente onde o anterior terminou.
    Sobra de tempo menor que a duração no fim de um intervalo é
    descartada (não cabe um atendimento inteiro).
    """
    slots: List[Interval] = []
    for start, end in free:
        cursor = start
        while cursor + slot_duration <= end:
            slots.append(Interval(cursor, cursor + slot_duration))
            cursor += slot_duration
    return slots