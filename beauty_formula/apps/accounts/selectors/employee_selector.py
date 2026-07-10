"""
Queries de Funcionário - Funções para buscar e filtrar funcionários.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404

from beauty_formula.apps.accounts.models import Employee
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.constants.gender import Gender


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_employee_by_id(employee_id: UUID) -> Optional[Employee]:
    """
    Retorna funcionário pelo ID.
    
    Args:
        employee_id: UUID do funcionário
        
    Returns:
        Optional[Employee]: Funcionário encontrado ou None
    """
    try:
        return Employee.objects.get(id=employee_id)
    except Employee.DoesNotExist:
        return None


def get_employee_or_404(employee_id: UUID) -> Employee:
    """
    Retorna funcionário pelo ID ou levanta 404.
    
    Args:
        employee_id: UUID do funcionário
        
    Returns:
        Employee: Funcionário encontrado
        
    Raises:
        Http404: Se o funcionário não existir
    """
    return get_object_or_404(Employee, id=employee_id)


def get_employee_by_user_id(user_id: UUID) -> Optional[Employee]:
    """
    Retorna funcionário pelo ID do usuário associado.
    
    Args:
        user_id: UUID do usuário
        
    Returns:
        Optional[Employee]: Funcionário encontrado ou None
    """
    try:
        return Employee.objects.get(user_id=user_id)
    except Employee.DoesNotExist:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Username
# ═══════════════════════════════════════════════════════════════════════════════

def get_employee_by_username(username: str, case_sensitive: bool = False) -> Optional[Employee]:
    """
    Retorna funcionário pelo username (exato).
    
    Args:
        username: Nome de usuário
        case_sensitive: Se True, busca case-sensitive
        
    Returns:
        Optional[Employee]: Funcionário encontrado ou None
    """
    if not username:
        return None
    
    if case_sensitive:
        return Employee.objects.filter(username=username).first()
    return Employee.objects.filter(username__iexact=username).first()


def get_employees_by_username_partial(username: str) -> List[Employee]:
    """
    Retorna funcionários que contenham o username (busca parcial).
    
    Args:
        username: Parte do nome de usuário
        
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    if not username:
        return []
    
    return Employee.objects.filter(username__icontains=username).select_related('user')


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Nome
# ═══════════════════════════════════════════════════════════════════════════════

def get_employees_by_first_name(first_name: str, exact: bool = False) -> List[Employee]:
    """
    Retorna funcionários pelo primeiro nome.
    
    Args:
        first_name: Primeiro nome
        exact: Se True, busca exata; False busca contém
        
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    if not first_name:
        return []
    
    if exact:
        return Employee.objects.filter(first_name__iexact=first_name).select_related('user')
    return Employee.objects.filter(first_name__icontains=first_name).select_related('user')


def get_employees_by_last_name(last_name: str, exact: bool = False) -> List[Employee]:
    """
    Retorna funcionários pelo sobrenome.
    
    Args:
        last_name: Sobrenome
        exact: Se True, busca exata; False busca contém
        
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    if not last_name:
        return []
    
    if exact:
        return Employee.objects.filter(last_name__iexact=last_name).select_related('user')
    return Employee.objects.filter(last_name__icontains=last_name).select_related('user')


def get_employees_by_full_name(full_name: str) -> List[Employee]:
    """
    Retorna funcionários pelo nome completo (busca em first_name OU last_name).
    
    Args:
        full_name: Nome completo ou parte dele
      
        
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    if not full_name:
        return []
    
    name_parts = full_name.strip().split()
    
    if len(name_parts) == 1:
        return Employee.objects.filter(
            Q(first_name__icontains=full_name) | 
            Q(last_name__icontains=full_name)
        ).select_related('user')
    else:
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:])
        
        return Employee.objects.filter(
            Q(first_name__icontains=first_name) & 
            Q(last_name__icontains=last_name)
        ).select_related('user')


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Email (via User)
# ═══════════════════════════════════════════════════════════════════════════════

def get_employee_by_email(email: str) -> Optional[Employee]:
    """
    Retorna funcionário pelo email do usuário associado.
    
    Args:
        email: Email do usuário
        
    Returns:
        Optional[Employee]: Funcionário encontrado ou None
    """
    if not email:
        return None
    
    try:
        return Employee.objects.select_related('user').get(user__email__iexact=email)
    except Employee.DoesNotExist:
        return None


def get_employees_by_email_partial(email: str) -> List[Employee]:
    """
    Retorna funcionários por parte do email.
    
    Args:
        email: Parte do email
        
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    if not email:
        return []
    
    return Employee.objects.filter(
        user__email__icontains=email
    ).select_related('user')


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Telefone
# ═══════════════════════════════════════════════════════════════════════════════

def get_employee_by_phone(phone: str) -> Optional[Employee]:
    """
    Retorna funcionário pelo telefone.
    
    Args:
        phone: Número de telefone
        
    Returns:
        Optional[Employee]: Funcionário encontrado ou None
    """
    if not phone:
        return None
    
    # Remove caracteres especiais
    import re
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    return Employee.objects.filter(phone__contains=clean_phone).first()


def get_employees_by_phone_partial(phone: str) -> List[Employee]:
    """
    Retorna funcionários que contenham parte do telefone.
    
    Args:
        phone: Parte do número de telefone
        
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    if not phone:
        return []
    
    import re
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    return Employee.objects.filter(
        phone__contains=clean_phone
    ).select_related('user')


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Instagram
# ═══════════════════════════════════════════════════════════════════════════════

def get_employee_by_instagram(instagram: str) -> Optional[Employee]:
    """
    Retorna funcionário pelo Instagram (URL ou username).
    
    Args:
        instagram: URL ou username do Instagram
        
    Returns:
        Optional[Employee]: Funcionário encontrado ou None
    """
    if not instagram:
        return None
    
    # Se for URL, extrai o username
    if 'instagram.com' in instagram:
        import re
        match = re.search(r'instagram\.com/([^/?]+)', instagram)
        if match:
            instagram = match.group(1)
    
    return Employee.objects.filter(
        Q(instagram__iexact=instagram) |
        Q(instagram__icontains=instagram)
    ).first()


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Data de Nascimento
# ═══════════════════════════════════════════════════════════════════════════════

def get_employees_by_birth_date(birth_date: date) -> List[Employee]:
    """
    Retorna funcionários com data de nascimento específica.
    
    Args:
        birth_date: Data de nascimento
        
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    if not birth_date:
        return []
    
    return Employee.objects.filter(
        birth_date=birth_date
    ).select_related('user')


def get_employees_by_birth_date_range(start_date: date, end_date: date) -> List[Employee]:
    """
    Retorna funcionários com data de nascimento em um intervalo.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    if not start_date or not end_date:
        return []
    
    return Employee.objects.filter(
        birth_date__gte=start_date,
        birth_date__lte=end_date
    ).select_related('user')


def get_employees_with_birthday_today() -> List[Employee]:
    """
    Retorna funcionários que fazem aniversário hoje.
    
    Returns:
        List[Employee]: Lista de funcionários aniversariantes
    """
    today = date.today()
    return Employee.objects.filter(
        birth_date__month=today.month,
        birth_date__day=today.day
    ).select_related('user')


def get_employees_with_birthday_in_month(month: int) -> List[Employee]:
    """
    Retorna funcionários que fazem aniversário em um mês específico.
    
    Args:
        month: Mês (1-12)
        
    Returns:
        List[Employee]: Lista de funcionários aniversariantes
    """
    if not 1 <= month <= 12:
        return []
    
    return Employee.objects.filter(
        birth_date__month=month
    ).select_related('user').order_by('birth_date__day')


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Gênero
# ═══════════════════════════════════════════════════════════════════════════════

def get_employees_by_gender(gender: str) -> List[Employee]:
    """
    Retorna funcionários por gênero.
    
    Args:
        gender: Gênero (Gender.MALE, Gender.FEMALE, Gender.OTHER
        
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    if not gender:
        return []
    
    return Employee.objects.filter(
        gender=gender
    ).select_related('user')


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Serviços
# ═══════════════════════════════════════════════════════════════════════════════

def get_employees_by_service(service_id: UUID) -> List[Employee]:
    """
    Retorna funcionários que prestam um serviço específico.
    
    Args:
        service_id: UUID do serviço
        
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    return Employee.objects.filter(
        services__id=service_id
    ).select_related('user').distinct()


def get_employees_by_services(service_ids: List[UUID]) -> List[Employee]:
    """
    Retorna funcionários que prestam pelo menos um dos serviços.
    
    Args:
        service_ids: Lista de UUIDs dos serviços
        
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    if not service_ids:
        return []
    
    return Employee.objects.filter(
        services__id__in=service_ids
    ).select_related('user').distinct()


def get_employees_with_services() -> List[Employee]:
    """
    Retorna funcionários que possuem serviços associados.
        
    Returns:
        List[Employee]: Lista de funcionários com serviços
    """
    return Employee.objects.filter(
        services__isnull=False
    ).select_related('user').distinct()


def get_employees_without_services() -> List[Employee]:
    """
    Retorna funcionários sem serviços associados.
    
    Returns:
        List[Employee]: Lista de funcionários sem serviços
    """
    return Employee.objects.filter(
        services__isnull=True
    ).select_related('user')


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Bio
# ═══════════════════════════════════════════════════════════════════════════════

def get_employees_by_bio_keyword(keyword: str) -> List[Employee]:
    """
    Retorna funcionários cuja bio contenha uma palavra-chave.
    
    Args:
        keyword: Palavra-chave para busca na bio
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    if not keyword:
        return []
    
    return Employee.objects.filter(bio__icontains=keyword).select_related('user')


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Combinadas
# ═══════════════════════════════════════════════════════════════════════════════

def search_employees(query: str, search_fields: List[str] = None) -> List[Employee]:
    """
    Busca funcionários em múltiplos campos.
    
    Args:
        query: Termo de busca
        search_fields: Campos para buscar (default: username, first_name, last_name, email, bio)
        
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    if not query:
        return []
    
    if search_fields is None:
        search_fields = ['username', 'first_name', 'last_name', 'user__email', 'bio']
    
    # Constrói Q objects para cada campo
    q_objects = Q()
    for field in search_fields:
        q_objects |= Q(**{f"{field}__icontains": query})
    
    return Employee.objects.filter(q_objects).select_related('user')


def get_employees_by_name_and_username(
    name: Optional[str] = None,
    username: Optional[str] = None,
) -> List[Employee]:
    """
    Busca funcionários por nome E/OU username.
    
    Args:
        name: Nome (busca parcial em first_name e last_name)
        username: Username (busca parcial)
        
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    q = Q()
    
    if name:
        q &= Q(first_name__icontains=name) | Q(last_name__icontains=name)
    
    if username:
        q &= Q(username__icontains=username)
    
    if not q:
        return []
    
    return Employee.objects.filter(q).select_related('user')


# ═══════════════════════════════════════════════════════════════════════════════
# Filtros Avançados
# ═══════════════════════════════════════════════════════════════════════════════

def filter_employees(
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    gender: Optional[str] = None,
    created_after: Optional[date] = None,
    created_before: Optional[date] = None,
    birth_date_after: Optional[date] = None,
    birth_date_before: Optional[date] = None,
    has_phone: Optional[bool] = None,
    has_instagram: Optional[bool] = None,
    has_photo: Optional[bool] = None,
    has_bio: Optional[bool] = None,
    has_services: Optional[bool] = None,
    service_id: Optional[UUID] = None,
    order_by: str = 'first_name',
) -> List[Employee]:
    """
    Filtra funcionários com múltiplos critérios.
    
    Args:
        is_active: Filtrar por status ativo
        is_verified: Filtrar por verificação de email
        gender: Filtrar por gênero
        created_after: Criados após esta data
        created_before: Criados antes desta data
        birth_date_after: Data de nascimento após
        birth_date_before: Data de nascimento antes
        has_phone: Tem telefone cadastrado
        has_instagram: Tem Instagram cadastrado
        has_photo: Tem foto cadastrada
        has_bio: Tem biografia cadastrada
        has_services: Tem serviços associados
        service_id: Filtrar por serviço específico
        order_by: Campo para ordenação
        
    Returns:
        List[Employee]: Lista de funcionários filtrados
    """
    q = Q()
    
    # Filtros do User
    if is_active is not None:
        q &= Q(user__is_active=is_active)
    
    if is_verified is not None:
        q &= Q(user__is_trusty=is_verified)
    
    # Filtros do Employee
    if gender:
        q &= Q(gender=gender)
    
    if created_after:
        q &= Q(user__date_joined__gte=created_after)
    
    if created_before:
        q &= Q(user__date_joined__lte=created_before)
    
    if birth_date_after:
        q &= Q(birth_date__gte=birth_date_after)
    
    if birth_date_before:
        q &= Q(birth_date__lte=birth_date_before)
    
    if service_id:
        q &= Q(services__id=service_id)
    
    # Filtros de campos preenchidos
    if has_phone is not None:
        if has_phone:
            q &= Q(phone__isnull=False) & ~Q(phone='')
        else:
            q &= Q(phone__isnull=True) | Q(phone='')
    
    if has_instagram is not None:
        if has_instagram:
            q &= Q(instagram__isnull=False) & ~Q(instagram='')
        else:
            q &= Q(instagram__isnull=True) | Q(instagram='')
    
    if has_photo is not None:
        if has_photo:
            q &= ~Q(photo='default/employee_img.jpeg') & Q(photo__isnull=False)
        else:
            q &= Q(photo='default/employee_img.jpeg') | Q(photo__isnull=True)
    
    if has_bio is not None:
        if has_bio:
            q &= Q(bio__isnull=False) & ~Q(bio='')
        else:
            q &= Q(bio__isnull=True) | Q(bio='')
    
    if has_services is not None:
        if has_services:
            q &= Q(services__isnull=False)
        else:
            q &= Q(services__isnull=True)
    
    if not q:
        return []
    
    return Employee.objects.filter(q).select_related('user').distinct().order_by(order_by)


# ═══════════════════════════════════════════════════════════════════════════════
# Utilitários
# ═══════════════════════════════════════════════════════════════════════════════

def validate_employee_exists(employee_id: UUID) -> bool:
    """
    Verifica se um funcionário existe.
    
    Args:
        employee_id: UUID do funcionário
        
    Returns:
        bool: True se existir, False caso contrário
    """
    return Employee.objects.filter(id=employee_id).exists()


def get_employee_full_name_display(employee: Employee) -> str:
    """
    Retorna o nome completo do funcionário para exibição.
    
    Args:
        employee: Instância do funcionário
        
    Returns:
        str: Nome completo formatado
    """
    if employee.first_name and employee.last_name:
        return f"{employee.first_name} {employee.last_name}"
    elif employee.first_name:
        return employee.first_name
    elif employee.last_name:
        return employee.last_name
    return employee.username or f"Funcionário {employee.id}"


def get_employee_contact_info(employee: Employee) -> Dict[str, Optional[str]]:
    """
    Retorna informações de contato do funcionário.
    
    Args:
        employee: Instância do funcionário
        
    Returns:
        Dict: Informações de contato
    """
    return {
        'email': employee.user.email if employee.user else None,
        'phone': employee.phone,
        'instagram': employee.instagram,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Bulk Operations
# ═══════════════════════════════════════════════════════════════════════════════

def get_employees_by_ids(employee_ids: List[UUID]) -> List[Employee]:
    """
    Retorna múltiplos funcionários por IDs.
    
    Args:
        employee_ids: Lista de UUIDs
        
    Returns:
        List[Employee]: Lista de funcionários encontrados
    """
    if not employee_ids:
        return []
    
    return Employee.objects.filter(
        id__in=employee_ids
    ).select_related('user')


def get_employees_without_phone() -> List[Employee]:
    """
    Retorna funcionários sem telefone cadastrado.
    
    Returns:
        List[Employee]: Lista de funcionários sem telefone
    """
    return Employee.objects.filter(
        Q(phone__isnull=True) | Q(phone='')
    ).select_related('user')


def get_employees_without_instagram() -> List[Employee]:
    """
    Retorna funcionários sem Instagram cadastrado.
    
    Returns:
        List[Employee]: Lista de funcionários sem Instagram
    """
    return Employee.objects.filter(
        Q(instagram__isnull=True) | Q(instagram='')
    ).select_related('user')


def get_employees_without_bio() -> List[Employee]:
    """
    Retorna funcionários sem biografia cadastrada.
    
    Returns:
        List[Employee]: Lista de funcionários sem biografia
    """
    return Employee.objects.filter(
        Q(bio__isnull=True) | Q(bio='')
    ).select_related('user')


__all__ = [
    # Por ID
    'get_employee_by_id',
    'get_employee_or_404',
    'get_employee_by_user_id',
    
    # Por Username
    'get_employee_by_username',
    'get_employees_by_username_partial',
    
    # Por Nome
    'get_employees_by_first_name',
    'get_employees_by_last_name',
    'get_employees_by_full_name',
    
    # Por Email
    'get_employee_by_email',
    'get_employees_by_email_partial',
    
    # Por Telefone
    'get_employee_by_phone',
    'get_employees_by_phone_partial',
    
    # Por Instagram
    'get_employee_by_instagram',
    
    # Por Data de Nascimento
    'get_employees_by_birth_date',
    'get_employees_by_birth_date_range',
    'get_employees_with_birthday_today',
    'get_employees_with_birthday_in_month',
    
    # Por Gênero
    'get_employees_by_gender',
    
    # Por Serviços
    'get_employees_by_service',
    'get_employees_by_services',
    'get_employees_with_services',
    'get_employees_without_services',
    
    # Por Bio
    'get_employees_by_bio_keyword',
    
    # Buscas combinadas
    'search_employees',
    'get_employees_by_name_and_username',
    
    # Filtros avançados
    'filter_employees',
    
    # Utilitários
    'validate_employee_exists',
    'get_employee_full_name_display',
    'get_employee_contact_info',
    
    # Bulk Operations
    'get_employees_by_ids',
    'get_employees_without_phone',
    'get_employees_without_instagram',
    'get_employees_without_bio',
]