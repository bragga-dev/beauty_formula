import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class AverageRating(models.Model):
    """
    Avaliação real deixada pelo cliente sobre um atendimento concluído.

    Model central do domínio de avaliações: é a única fonte de dados brutos.
    ServiceAverageRating e EmployeeAverageRating são agregados derivados
    dela, recalculados explicitamente pelo service layer (ReviewService)
    — não há signal nem lógica de atualização aqui no model.
    """

    class RatingChoices(models.IntegerChoices):
        ONE_STAR = 1, _("⭐ 1 Estrela - Péssimo")
        TWO_STARS = 2, _("⭐⭐ 2 Estrelas - Ruim")
        THREE_STARS = 3, _("⭐⭐⭐ 3 Estrelas - Regular")
        FOUR_STARS = 4, _("⭐⭐⭐⭐ 4 Estrelas - Bom")
        FIVE_STARS = 5, _("⭐⭐⭐⭐⭐ 5 Estrelas - Excelente")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    scheduling = models.OneToOneField(
        "services.Scheduling",
        on_delete=models.PROTECT,
        related_name="rating",
        verbose_name=_("Agendamento"),
        help_text=_("Agendamento concluído que originou esta avaliação."),
    )

    client = models.ForeignKey(
        "accounts.Client",
        on_delete=models.PROTECT,
        related_name="service_ratings",
        verbose_name=_("Cliente"),
    )
    employee = models.ForeignKey(
        "accounts.Employee",
        on_delete=models.PROTECT,
        related_name="service_ratings",
        verbose_name=_("Profissional"),
    )
    service = models.ForeignKey(
        "services.Service",
        on_delete=models.PROTECT,
        related_name="service_ratings",
        verbose_name=_("Serviço"),
    )

    rating = models.PositiveSmallIntegerField(
        _("Avaliação"),
        choices=RatingChoices.choices,
        help_text=_("Nota de 1 a 5 estrelas"),
    )
    comment = models.TextField(
        _("Comentário"),
        blank=True,
        null=True,
        max_length=500,
        help_text=_("Deixe um comentário sobre sua experiência"),
    )

    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)
    is_authorized = models.BooleanField(_("Autorizado"), default=False)

    class Meta:
        verbose_name = _("Avaliação de serviço")
        verbose_name_plural = _("Avaliações de serviços")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "service", "employee"],
                name="unique_rating_per_client_service_employee",
            ),
        ]
        indexes = [
            models.Index(fields=["employee"]),
            models.Index(fields=["service"]),
            models.Index(fields=["client"]),
            models.Index(fields=["rating"]),
        ]

    def __str__(self):
        return f"{self.client} → {self.employee} ({self.service.name}): {self.rating}★"

    def clean(self):
        """
        Garante consistência com o agendamento vinculado: a avaliação só
        pode existir para um agendamento CONCLUÍDO, e os campos
        denormalizados (client/employee/service) devem corresponder ao
        que está registrado em `scheduling` — evita divergência de dados
        entre a avaliação e o agendamento que a originou.
        """
        if self.scheduling_id:
            if self.scheduling.status != self.scheduling.SchedulingStatus.COMPLETED:
                raise ValidationError({"scheduling": _("Só é possível avaliar agendamentos concluídos.")})
            if self.client_id and self.client_id != self.scheduling.client_id:
                raise ValidationError({"client": _("Cliente não corresponde ao agendamento.")})
            if self.employee_id and self.employee_id != self.scheduling.employee_id:
                raise ValidationError({"employee": _("Profissional não corresponde ao agendamento.")})
            if self.service_id and self.service_id != self.scheduling.service_id:
                raise ValidationError({"service": _("Serviço não corresponde ao agendamento.")})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)