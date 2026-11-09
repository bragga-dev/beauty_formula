# type: ignore
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from beauty_formula.apps.core.validators.image_validator import validate_image_file
from beauty_formula.apps.accounts.models.user import User
from datetime import timezone
from django.utils import timezone 


def manager_photo_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"photos/{instance.id}/{uuid.uuid4().hex}.{ext}"

DEFAULT_MANAGER_PHOTO = "default/manager_img.jpg"


class Manager(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="client_profile")
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(_("Nome"), max_length=255, blank=True, null=True)
    last_name = models.CharField(_("Sobrenome"), max_length=255, blank=True, null=True)
    photo = models.ImageField(upload_to=manager_photo_path, default=DEFAULT_MANAGER_PHOTO, blank=True, null=True, validators=[validate_image_file], help_text=_('Formatos aceitos: jpg, jpeg ou png. Máx: 5MB.'))

    def __str__(self):
        email = self.user.email if self.user else "desvinculado"
        return f"{self.first_name} {self.last_name} ({email})"
    
    class Meta:
        verbose_name = _("Gerente")
        verbose_name_plural = _("Gerentes")
        indexes = [
            models.Index(fields=["first_name", "last_name"]),
        ]
        ordering = ["first_name", "last_name"]


    @property
    def photo_url(self) -> str:
        if self.photo and self.photo.name != DEFAULT_MANAGER_PHOTO:
            try:
                return self.photo.url
            except Exception:
                pass
        return self.photo.storage.url(DEFAULT_MANAGER_PHOTO)    
    

    def get_full_name(self):
        full_name = " ".join(filter(None, [self.first_name, self.last_name])).strip()
        return full_name or f"Client {self.id}"
    
  
    def clean(self):
        if self.birth_date and self.birth_date > timezone.now().date():
            raise ValidationError(
                {'birth_date': _('Data de nascimento não pode ser no futuro.')}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.photo:
            self.photo = DEFAULT_MANAGER_PHOTO
        super().save(*args, **kwargs)