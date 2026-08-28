"""
Gera, de uma vez só, a comissão PENDING de todo atendimento COMPLETED que
ainda não tem comissão registrada — cobre o histórico retroativo (tudo que
foi concluído antes da geração automática existir).

Depois que a geração automática entrou em
`complete_scheduling_for_employee` e `auto_complete_overdue_scheduling`,
este comando deixa de fazer parte do fluxo do dia a dia: é uma ferramenta
de manutenção, rodada uma vez (ou sob demanda, se algo escapar), não um
botão do painel.

Uso:
    python manage.py backfill_commissions
    python manage.py backfill_commissions --dry-run
"""
from django.core.management.base import BaseCommand

from beauty_formula.apps.core.exceptions.payment_exception import CommissionAlreadyExists
from beauty_formula.apps.payment.selectors.employee_commission_selector import (
    list_completed_schedulings_without_commission,
)
from beauty_formula.apps.payment.services.employee_commission_service import (
    generate_commission_for_completed_scheduling,
)


class Command(BaseCommand):
    help = (
        "Gera retroativamente a comissão PENDING de todo atendimento "
        "COMPLETED que ainda não tem comissão registrada."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Só lista quantos atendimentos seriam afetados, sem criar nada.",
        )

    def handle(self, *args, **options):
        schedulings = list(list_completed_schedulings_without_commission())
        total = len(schedulings)

        if options["dry_run"]:
            self.stdout.write(f"{total} atendimento(s) COMPLETED sem comissão seriam gerados agora.")
            return

        created = 0
        skipped = 0
        for scheduling in schedulings:
            try:
                result = generate_commission_for_completed_scheduling(scheduling)
            except CommissionAlreadyExists:
                skipped += 1
                continue
            if result is None:
                skipped += 1
            else:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill concluído: {created} comissão(ões) gerada(s), {skipped} ignorada(s) "
                f"(já existiam), de {total} atendimento(s) analisado(s)."
            )
        )