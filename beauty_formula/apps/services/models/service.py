import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from beauty_formula.apps.core.validators.image_validator import validate_image_file


def service_image_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"photos/{instance.id}/photo.{ext}"


DEFAULT_SERVICE_PHOTO = "default/service_img.png"


class Service(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Nome do serviço"), max_length=255)
    description = models.TextField(_("Descrição do serviço"), blank=True, null=True)
    price = models.DecimalField(_("Preço do serviço"), max_digits=10, decimal_places=2, validators=[MinValueValidator(0, message=_("O preço não pode ser negativo"))])
    image = models.ImageField(
        _("Imagem do serviço"),
        upload_to=service_image_path,
        validators=[validate_image_file],
        default=DEFAULT_SERVICE_PHOTO,
        blank=True,
        null=True,
        help_text=_("Formatos aceitos: jpg, jpeg ou png. Máx: 5MB."),
    )
    total_bookings = models.PositiveIntegerField(_("Total de agendamentos"), default=0, editable=False, help_text=_("Número total de vezes que este serviço foi agendado"))
    commission_percentage = models.DecimalField(_("Comissão (%)"), max_digits=5, decimal_places=2, default=70, help_text=_("Percentual de comissão para o funcionário (70 = padrão do sistema)"))
    duration = models.DurationField(_("Duração do serviço"), default=timedelta(minutes=30), validators=[MinValueValidator(timedelta(minutes=1), message=_("A duração deve ser de pelo menos 1 minuto"))])
    is_active = models.BooleanField(_("Ativo?"), default=True)

    def __str__(self):
        return self.name

    @property
    def image_url(self) -> str:
        """
        Retorna a URL da imagem no MinIO.
        Nunca lança erro: se a imagem não existir no bucket, devolve a URL do padrão.
        """
        default_image = self._meta.get_field("image").default
        if self.image and self.image.name != default_image:
            try:
                return self.image.url
            except Exception:
                pass
        return self.image.storage.url(default_image)

    def increment_bookings(self) -> None:
        """Incrementa total_bookings de forma atômica (evita race condition)."""
        type(self).objects.filter(pk=self.pk).update(total_bookings=F("total_bookings") + 1)

    def decrement_bookings(self) -> None:
        """Decrementa total_bookings de forma atômica, nunca abaixo de zero."""
        type(self).objects.filter(pk=self.pk, total_bookings__gt=0).update(total_bookings=F("total_bookings") - 1)

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.image:
            self.image = DEFAULT_SERVICE_PHOTO
        super().save(*args, **kwargs)

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