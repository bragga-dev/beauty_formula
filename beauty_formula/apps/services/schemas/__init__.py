"""
Schemas do módulo de serviços — validação e serialização para
Service, EmployeeService, EmployeeTimeOff, EmployeeWorkingHours
e Availability.

IMPORTANTE sobre EmployeeService: `EmployeeServicePrivateOut`
(em employee_service_schema.py) precisa de `EmployeeOut`
(accounts.schemas.employee_schema), que por sua vez importa
`ServiceOut` daqui (services.schemas.service_schema). Importar
`employee_service_schema` aqui no agregador do pacote forçaria esse
ciclo toda vez que QUALQUER coisa deste pacote fosse importada —
já aconteceu isso em produção (ImportError: cannot import name
'EmployeeOut' from partially initialized module). Como nada no
projeto consome esse agregador (todo mundo importa direto do
submódulo, ex: `from ...schemas.employee_service_schema import X`),
a saída mais segura é não reexportar esse módulo específico aqui.
"""
from beauty_formula.apps.services.schemas.service_schema import (
    ServiceCreateIn,
    ServiceFilter,
    ServiceOut,
    ServicePrivateOut,
    ServiceUpdateIn,
    ServiceUpdateStatusIn,
)

from beauty_formula.apps.services.schemas.employee_time_off_schema import (
    BlockTypeEnum,
    BlockModalityEnum,
    EmployeeTimeOffRecurringCreateIn,
    EmployeeTimeOffPunctualCreateIn,
    EmployeeTimeOffList,
    EmployeeTimeOffOut,
    EmployeeTimeOffRecurringUpdateIn,
    EmployeeTimeOffPunctualUpdateIn,
)

from beauty_formula.apps.services.schemas.employee_working_hours_schema import (
    EmployeeWorkingHoursCreateIn,
    EmployeeWorkingHoursOut,
    EmployeeWorkingHoursUpdateIn,
    WeekdayEnum,
)

from beauty_formula.apps.services.schemas.scheduling_schema import (

    SchedulingStatusEnum,
    SchedulingOut,
    SchedulingPrivateOut,
    SchedulingCreateIn,
    SchedulingUpdateIn,
    SchedulingCancelIn,
    SchedulingStatusUpdateIn,
    SchedulingFilter,
    SchedulingList,
    SchedulingPrivateList,
)

from beauty_formula.apps.services.schemas.availability_schema import (
    AvailabilitySlotOut,
)


__all__ = [
    
    # Serviços
    "ServiceCreateIn",
    "ServiceFilter",
    "ServiceOut",
    "ServicePrivateOut",
    "ServiceUpdateIn",
    "ServiceUpdateStatusIn",

    # Pausa e Bloqueios dos Funcíonários
    "BlockTypeEnum",
    "BlockModalityEnum",
    "EmployeeTimeOffRecurringCreateIn",
    "EmployeeTimeOffPunctualCreateIn",
    "EmployeeTimeOffList",
    "EmployeeTimeOffOut",
    "EmployeeTimeOffRecurringUpdateIn",
    "EmployeeTimeOffPunctualUpdateIn",
    
    # Horas de Trabalho dos Funcionários
    "EmployeeWorkingHoursCreateIn",
    "EmployeeWorkingHoursOut",
    "EmployeeWorkingHoursUpdateIn",
    "WeekdayEnum",

    # Agendamentos
    "SchedulingStatusEnum",
    "SchedulingOut",
    "SchedulingPrivateOut",
    "SchedulingCreateIn",
    "SchedulingUpdateIn",
    "SchedulingCancelIn",
    "SchedulingStatusUpdateIn",
    "SchedulingFilter",
    "SchedulingList",
    "SchedulingPrivateList",
    
    # Disponibilidade
    "AvailabilitySlotOut",

    # EmployeeService: importe direto de
    # beauty_formula.apps.services.schemas.employee_service_schema
    # (EmployeeServiceCreateIn, EmployeeServiceOut,
    # EmployeeServicePrivateOut, EmployeeServiceUpdateIn) — não
    # reexportado aqui de propósito, ver docstring do módulo.
]