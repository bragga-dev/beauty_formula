# Migration escrita manualmente (não pelo `makemigrations` puro) porque o
# autodetector do Django ordena as operações de um jeito que quebra aqui:
#
# 1. Ele colocava o AddConstraint (que referencia `slot_range`) ANTES do
#    AddField que cria a própria coluna `slot_range` — falha na hora de
#    aplicar.
# 2. Faltava o backfill de `scheduled_end_time` pra linhas já existentes.
#    Sem isso, em qualquer banco que já tenha agendamentos (ou seja,
#    qualquer banco de produção), a coluna gerada `slot_range` nasceria
#    com o limite superior nulo (`tstzrange(scheduled_time, NULL)`) pra
#    todo registro antigo — silenciosamente errado, não dá erro nenhum.
# 3. Faltava a extensão `btree_gist`, obrigatória pro índice GiST da
#    ExclusionConstraint suportar o operador "=" sobre `employee` (UUID)
#    combinado com "&&" sobre o range.
#
# Ordem correta: extensão -> campos novos -> backfill -> coluna gerada ->
# constraint.

import django.contrib.postgres.constraints
import django.contrib.postgres.fields.ranges
from django.conf import settings
from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations, models


def backfill_scheduled_end_time(apps, schema_editor):
    Scheduling = apps.get_model("services", "Scheduling")
    # .iterator() + update em lote via .update() direto no queryset seria
    # mais rápido que F()-expression aqui porque duration_at_booking é
    # DurationField (interval) e scheduled_time é DateTimeField — dá pra
    # fazer isso inteiramente no banco com uma única query UPDATE.
    Scheduling.objects.filter(scheduled_end_time__isnull=True).update(
        scheduled_end_time=models.F("scheduled_time") + models.F("duration_at_booking")
    )


def noop_reverse(apps, schema_editor):
    """Nada a desfazer — RemoveField de scheduled_end_time já limpa os dados."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_sessionmetadata'),
        ('services', '0017_scheduling_completed_at'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Necessária pro ExclusionConstraint no fim desta migration: sem
        # ela, a criação do índice GiST falha porque não existe operator
        # class btree_gist pra comparar UUID por "=" dentro de um GiST.
        BtreeGistExtension(),

        migrations.AddField(
            model_name='scheduling',
            name='commission_percentage_at_booking',
            field=models.DecimalField(
                decimal_places=2, editable=False, max_digits=5, null=True,
                verbose_name='Comissão (%) no momento do agendamento',
                help_text=(
                    'Snapshot do commission_percentage do Service no momento em que '
                    'o agendamento foi criado. Garante que a comissão gerada na '
                    'conclusão reflita a regra vigente quando o cliente agendou, não '
                    'uma mudança feita pelo admin depois — mesmo racional de '
                    'price_at_booking/duration_at_booking. Nulo só em registros '
                    'criados antes desse campo existir.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='scheduling',
            name='scheduled_end_time',
            field=models.DateTimeField(
                editable=False, null=True,
                verbose_name='Horário de término (calculado)',
                help_text=(
                    'scheduled_time + duration_at_booking, calculado em save(). '
                    'Existe como coluna persistida (em vez de só a property '
                    '`end_time`) porque `slot_range` (abaixo) precisa referenciar '
                    'duas colunas de timestamp diretamente — `tstzrange()` sobre '
                    'duas colunas é IMMUTABLE, mas `scheduled_time + interval` não '
                    'é (Postgres não garante isso na presença de componente de mês/'
                    'DST no interval), e coluna GENERATED exige expressão IMMUTABLE.'
                ),
            ),
        ),

        # Backfill: precisa rodar ANTES de criar a coluna gerada, senão
        # todo agendamento já existente vira um range com limite superior
        # nulo (aberto) em vez do horário de término real.
        migrations.RunPython(backfill_scheduled_end_time, noop_reverse),

        migrations.AddField(
            model_name='scheduling',
            name='slot_range',
            field=models.GeneratedField(
                db_persist=True,
                expression=models.Func(
                    models.F('scheduled_time'),
                    models.F('scheduled_end_time'),
                    function='tstzrange',
                    output_field=django.contrib.postgres.fields.ranges.DateTimeRangeField(),
                ),
                output_field=django.contrib.postgres.fields.ranges.DateTimeRangeField(),
                verbose_name='Intervalo do horário (gerado)',
                help_text=(
                    'Coluna calculada pelo próprio Postgres (GENERATED ALWAYS AS) — '
                    '[scheduled_time, scheduled_end_time). Existe só pra sustentar o '
                    'ExclusionConstraint abaixo; não é lida pela aplicação.'
                ),
            ),
        ),

        migrations.AddConstraint(
            model_name='scheduling',
            constraint=django.contrib.postgres.constraints.ExclusionConstraint(
                condition=models.Q(('is_active', True), ('status', 'confirmed')),
                expressions=[('employee', '='), ('slot_range', '&&')],
                name='exclude_overlapping_confirmed_slots_per_employee',
                violation_error_message='Funcionário já possui outro agendamento CONFIRMADO nesse horário.',
            ),
        ),
    ]