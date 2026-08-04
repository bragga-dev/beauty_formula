"""
Client Repository — persistência de perfil Membro.
"""
from typing import Optional
from django.core.files.uploadedfile import InMemoryUploadedFile
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.accounts.schemas.client_schema import GenderEnum
from django.core.files import File
from beauty_formula.apps.core.tasks.media import delete_old_media_file

from typing import Optional

def create_employee(
    user: User,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    username: Optional[str] = None,
    phone: Optional[str] = None,
    gender: Optional[GenderEnum] = None,
    birth_date: Optional[str] = None,
    instagram: Optional[str] = None,
    photo: Optional[File] = None,
) -> Employee:
    fields = {
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "phone": phone,
            "gender": gender,
            "birth_date": birth_date,
            "instagram": instagram,
            "photo": photo,
        }
    fields = {k: v for k, v in fields.items() if v is not None}
    employee = Employee(user=user, **fields)
    employee.save()
    return employee



def update_employee(employee: Employee, **fields) -> Employee:
    for attr, value in fields.items():
        if value is not None:
            setattr(employee, attr, value)
    employee.full_clean()   
    employee.save()
    return employee


def delete_employee(employee: Employee) -> None:
    employee.delete()



def set_employee_photo(employee: Employee, photo: InMemoryUploadedFile) -> Employee:
    old_name = employee.photo.name if employee.photo and employee.photo.name != "default/employee_img.jpeg" else None
    employee.photo = photo
    employee.save(update_fields=["photo"])
    if old_name:
        delete_old_media_file.delay(old_name)
    return employee


def remove_employee_photo(employee: Employee) -> Employee:
    old_name = employee.photo.name if employee.photo and employee.photo.name != "default/employee_img.jpeg" else None
    employee.photo = "default/employee_img.jpeg"
    employee.save(update_fields=["photo"])
    if old_name:
        delete_old_media_file.delay(old_name)
    return employee