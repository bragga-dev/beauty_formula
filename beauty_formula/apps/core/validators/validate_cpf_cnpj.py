from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import logging
from validate_docbr import CPF, CNPJ


logger = logging.getLogger(__name__)





_cpf  = CPF()
_cnpj = CNPJ()

def validate_cpf(value):
    if not _cpf.validate(value):
        raise ValidationError(_('CPF inválido.'))

def validate_cnpj(value):
    if not _cnpj.validate(value):
        raise ValidationError(_('CNPJ inválido.'))