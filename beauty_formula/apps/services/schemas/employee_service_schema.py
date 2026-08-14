import uuid
from datetime import datetime

from ninja import Schema

from beauty_formula.apps.services.schemas.service_schema import ServiceOut
from beauty_formula.apps.accounts.schemas.employee_schema import EmployeeOut

class EmployeeServiceOut(Schema):
    """
    Vínculo entre funcionário e serviço — visão do próprio funcionário.
    Não expõe employee_id/employee: nesse contexto o funcionário já é o
    dono da lista (endpoint filtra por request.auth), não precisa
    repetir quem ele é. Os demais atributos do model (id, service_id,
    service, is_active, created_at) aparecem todos — o funcionário
    precisa ver is_active pra saber quais vínculos estão ativos/inativos
    na própria listagem, já que é ele quem ativa/desativa/exclui.
    """
    id: uuid.UUID
    service_id: uuid.UUID
    service: ServiceOut
    is_active: bool
    created_at: datetime


class EmployeeServicePrivateOut(Schema):
    """
    Vínculo entre funcionário e serviço — visão administrativa. Inclui
    employee_id porque aqui o admin enxerga vínculos de vários
    funcionários ao mesmo tempo, não só os de um.
    """
    id: uuid.UUID
    employee_id: uuid.UUID
    employee: EmployeeOut
    service_id: uuid.UUID
    service: ServiceOut
    is_active: bool
    created_at: datetime


class EmployeeServiceCreateIn(Schema):
    """
    Funcionário vincula um serviço que ele passa a atender.
    employee_id não entra aqui de propósito — vem de request.auth no
    router, nunca do payload (senão dá pra vincular em nome de outro).
    """
    service_id: uuid.UUID


class EmployeeServiceUpdateIn(Schema):
    """Ativa ou desativa um vínculo já existente entre funcionário e serviço."""
    active: bool


__all__ = [
    
    "EmployeeServiceOut",
    "EmployeeServicePrivateOut",
    "EmployeeServiceCreateIn",
    "EmployeeServiceUpdateIn",
]