
import uuid


from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from beauty_formula.apps.core.validators.image_validator import validate_image_file






class Service(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Nome do serviço"), max_length=255)
    description = models.TextField(_("Descrição do serviço"), blank=True, null=True)
    price = models.DecimalField(_("Preço do serviço"), max_digits=10, decimal_places=2)
    duration = models.DurationField(_("Duração do serviço"), blank=True, null=True)
    image = models.ImageField(_("Imagem do serviço"), upload_to="services/", validators=[validate_image_file], default="default/service_img.jpg")
    total_bookings = models.PositiveIntegerField(_("Total de agendamentos"), default=0, editable=False, help_text=_("Número total de vezes que este serviço foi agendado"))
    commission_percentage = models.DecimalField(_("Comissão (%)"), max_digits=5, decimal_places=2, default=70, help_text=_("Percentual de comissão para o funcionário (70 = padrão do sistema)"))

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _("Serviço")
        verbose_name_plural = _("Serviços")
        indexes = [
            models.Index(fields=["name"]),
        ]
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name"], name="unique_service_name")
        ]