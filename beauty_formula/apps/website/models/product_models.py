import uuid
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from beauty_formula.apps.core.validators.image_validator import validate_image_file



def product_image_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"photos/{instance.id}/{uuid.uuid4().hex}.{ext}"


DEFAULT_PRODUCT_PHOTO = "default/product_img.png"


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Nome do produto"), max_length=255, unique=True, blank=False, null=False)
    description = models.TextField(_("Descrição do produto"), blank=True, null=True)
    price = models.DecimalField(_("Preço do produto"), max_digits=10, decimal_places=2, validators=[MinValueValidator(0, message="O preço não pode ser negativo")])
    image = models.ImageField(_("Imagem do produto"), upload_to=product_image_path, validators=[validate_image_file], default=DEFAULT_PRODUCT_PHOTO, blank=True,  null=True, help_text=_("Formatos aceitos: jpg, jpeg ou png. Máx: 5MB."),)
    is_active = models.BooleanField(_("Ativo?"), default=True)
    stock = models.PositiveIntegerField(_("Estoque do produto"), default=0, validators=[MinValueValidator(0, message="O estoque não pode ser negativo")])
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


    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.image:
            self.image = DEFAULT_PRODUCT_PHOTO
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Produto")
        verbose_name_plural = _("Produtos")
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["price"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["stock"]),

        ]
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name"], name="unique_product_name")
        ]