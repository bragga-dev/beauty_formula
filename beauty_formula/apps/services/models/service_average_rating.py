import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class ServiceAverageRating(models.Model):
    """
    Agregado de avaliações por serviço. Cache de leitura: recalculado
    explicitamente pelo service layer (ReviewService) sempre que uma
    Average Rating relacionada ao serviço é criada, atualizada ou removida.
    Não contém lógica de agregação — apenas armazena o resultado.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.OneToOneField("services.Service", on_delete=models.CASCADE, related_name="average_rating", verbose_name=_("Serviço"))
    average_rating = models.DecimalField(_("Avaliação média"), max_digits=3, decimal_places=1, default=0.0)
    total_reviews = models.PositiveIntegerField(_("Total de avaliações"), default=0)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Média de avaliação do serviço")
        verbose_name_plural = _("Médias de avaliação dos serviços")

    def __str__(self):
        return f"{self.service.name}: {self.average_rating}★ ({self.total_reviews} avaliações)"

    def apply(self, average_rating, total_reviews):
        """Atualiza e persiste os valores já calculados pelo service layer."""
        self.average_rating = average_rating
        self.total_reviews = total_reviews
        self.save(update_fields=["average_rating", "total_reviews", "updated_at"])