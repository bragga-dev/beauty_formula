import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class EmployeeService(models.Model):
    """Modelo que representa quais serviços um funcionário está apto a atender."""
    employee = models.ForeignKey("accounts.Employee", on_delete=models.PROTECT, related_name="service_assignments")
    service = models.ForeignKey("services.Service", on_delete=models.PROTECT, related_name="employee_assignments")
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active = models.BooleanField(_("Ativo"), default=True)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)

    def __str__(self):
        return f"{self.employee} - {self.service}"

    class Meta:
        verbose_name = _("Serviço por Funcionário")
        verbose_name_plural = _("Serviços por Funcionários")
        ordering = ["employee", "service"]
        indexes = [
            models.Index(fields=["employee", "service"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["employee", "service"], name="unique_employee_service"),
        ]