from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image, UnidentifiedImageError
import os
from django.core.exceptions import ValidationError
import logging
from ninja import UploadedFile



logger = logging.getLogger(__name__)


# =========================================================
# VALIDAÇÃO DE IMAGEM
# =========================================================

VALID_FORMATS = {"JPEG", "PNG", "WEBP"}
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_SIZE_MB = 5
MAX_WIDTH = 4000
MAX_HEIGHT = 4000


def validate_image_file(value):
    if not isinstance(value, UploadedFile):
        return

    # 1. Valida extensão do arquivo antes de abrir
    ext = os.path.splitext(value.name)[-1].lower()
    if ext not in VALID_EXTENSIONS:
        raise ValidationError(
            _("Extensão inválida '%(ext)s'. Use: %(valid)s."),
            params={"ext": ext, "valid": ", ".join(sorted(VALID_EXTENSIONS))},
        )

    # 2. Valida tamanho do arquivo antes de abrir (mais eficiente)
    if value.size > MAX_SIZE_MB * 1024 * 1024:
        raise ValidationError(
            _("O arquivo (%(size).1f MB) excede o limite de %(max)s MB."),
            params={"size": value.size / (1024 * 1024), "max": MAX_SIZE_MB},
        )

    # 3. Abre e verifica a integridade da imagem
    try:
        value.seek(0)
        img = Image.open(value)
        img.verify()  # Detecta arquivos corrompidos
    except UnidentifiedImageError:
        raise ValidationError(_("O arquivo não é uma imagem reconhecida."))
    except Exception:
        raise ValidationError(_("Arquivo inválido ou corrompido."))
    finally:
        value.seek(0)  # Garante reset mesmo em caso de erro

    # 4. Reabre após verify() (obrigatório — verify() invalida o objeto)
    try:
        img = Image.open(value)
        img_format = img.format or ""

        # 5. Valida formato real (não apenas extensão)
        if img_format.upper() not in VALID_FORMATS:
            raise ValidationError(
                _("Formato '%(fmt)s' não suportado. Use: %(valid)s."),
                params={"fmt": img_format, "valid": ", ".join(sorted(VALID_FORMATS))},
            )

        # 6. Valida dimensões
        width, height = img.size
        if width > MAX_WIDTH or height > MAX_HEIGHT:
            raise ValidationError(
                _("A imagem (%(w)dx%(h)d px) excede o limite de %(mw)dx%(mh)d px."),
                params={
                    "w": width, "h": height,
                    "mw": MAX_WIDTH, "mh": MAX_HEIGHT,
                },
            )

        # 7. Bloqueia pixel bomb (imagens com dimensões enganosas)
        if width * height > MAX_WIDTH * MAX_HEIGHT:
            raise ValidationError(_("A imagem possui muitos pixels e pode sobrecarregar o servidor."))

    except ValidationError:
        raise
    except Exception:
        raise ValidationError(_("Não foi possível processar a imagem."))
    finally:
        value.seek(0)  # Deixa o arquivo pronto para uso posterior
