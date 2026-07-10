
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from beauty_formula.apps.core.validators.image_validator import validate_image_file
from beauty_formula.apps.accounts .models.user import User
from beauty_formula.apps.core.constants.gender import Gender


def employee_photo_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"photos/{instance.id}/photo.{ext}"

DEFAULT_EMPLOYEE_PHOTO = "default/employee_img.jpeg"



class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee_profile")
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(_("Nome"), max_length=255, blank=True, null=True)
    last_name = models.CharField(_("Sobrenome"), max_length=255, blank=True, null=True)
    username = models.CharField(_("Nome de usuário"), max_length=150, unique=True, blank=True, null=True)
    phone = models.CharField(_("Telefone"), max_length=20, blank=True, null=True, help_text=_("Número de telefone do funcionário."))
    birth_date = models.DateField(_("Data de nascimento"), blank=True, null=True)
    bio = models.TextField(_("Biografia"), blank=True, null=True, help_text=_("Breve descrição sobre o funcionário."))
    gender = models.CharField(_("Gênero"), max_length=10, choices=Gender.CHOICES, default=Gender.OTHER) 
    instagram = models.URLField(_("Instagram"), max_length=255, blank=True, null=True, help_text=_("URL do perfil do Instagram do funcionário."))
    photo = models.ImageField(upload_to=employee_photo_path, default=DEFAULT_EMPLOYEE_PHOTO, blank=True, null=True, validators=[validate_image_file], help_text=_('Formatos aceitos: jpg, jpeg ou png. Máx: 5MB.'))

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user.email})"
    

    class Meta:
        verbose_name = _("Funcionário")
        verbose_name_plural = _("Funcionários")
        indexes = [
            models.Index(fields=["first_name", "last_name"]),
        ]
        ordering = ["first_name", "last_name"]

    @property
    def photo_url(self) -> str:
        """
        Retorna a URL da foto no MinIO.
        Nunca lança erro: se a foto não existir no bucket, devolve a URL do padrão.
        Use {{ user.photo_url }} nos templates em vez de {{ user.photo.url }}.
        """
        if self.photo and self.photo.name != DEFAULT_EMPLOYEE_PHOTO:
            try:
                return self.photo.url
            except Exception:
                pass
        return self.photo.storage.url(DEFAULT_EMPLOYEE_PHOTO)    
    
    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username or f"Employee {self.id}"

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.photo:
            self.photo = DEFAULT_EMPLOYEE_PHOTO
        super().save(*args, **kwargs)