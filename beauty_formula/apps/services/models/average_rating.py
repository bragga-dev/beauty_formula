
import uuid


from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _




class AverageRating(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheduling = models.ForeignKey('services.Scheduling', on_delete=models.PROTECT, related_name="average_ratings_scheduling")
    average_rating = models.DecimalField(_("Avaliação média"), max_digits=3, decimal_places=2, default=0.00, help_text=_("Avaliação média do serviço, calculada com base nas avaliações dos clientes."))
    total_reviews = models.PositiveIntegerField(_("Total de avaliações"), default=0, editable=False, help_text=_("Número total de avaliações recebidas para este serviço."))
    total_rating = models.PositiveIntegerField(_("Soma das avaliações"), default=0, editable=False, help_text=_("Soma de todas as avaliações recebidas para este serviço, usada para calcular a avaliação média."))
    comments = models.TextField(_("Comentários"), blank=True, null=True, help_text=_("Comentários dos clientes sobre o serviço."), default="")
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)


    def __str__(self):
        return f"Avaliação média do agendamento {self.scheduling.id}: {self.average_rating} ({self.total_reviews} avaliações)"  
    
    class Meta:
        verbose_name = _("Avaliação média")
        verbose_name_plural = _("Avaliações médias")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["scheduling"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["scheduling"], name="unique_average_rating_per_scheduling")
        ]