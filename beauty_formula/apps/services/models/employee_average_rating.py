import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class EmployeeAverageRating(models.Model):
    """
    Agregado de avaliações por funcionário. Cache de leitura: recalculado
    explicitamente pelo service layer (ReviewService) sempre que uma
    Average Rating relacionada ao funcionário é criada, atualizada ou
    removida. Não contém lógica de agregação — apenas armazena o resultado.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.OneToOneField("accounts.Employee", on_delete=models.CASCADE, related_name="average_rating", verbose_name=_("Profissional"))
    average_rating = models.DecimalField(_("Avaliação média"), max_digits=3, decimal_places=1, default=0.0)
    total_reviews = models.PositiveIntegerField(_("Total de avaliações"), default=0)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Média de avaliação do funcionário")
        verbose_name_plural = _("Médias de avaliação dos funcionários")

    def __str__(self):
        return f"{self.employee}: {self.average_rating}★ ({self.total_reviews} avaliações)"

    def apply(self, average_rating, total_reviews):
        """Atualiza e persiste os valores já calculados pelo service layer."""
        self.average_rating = average_rating
        self.total_reviews = total_reviews
        self.save(update_fields=["average_rating", "total_reviews", "updated_at"])