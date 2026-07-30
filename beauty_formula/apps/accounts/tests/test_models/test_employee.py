import pytest
import uuid
from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.core.constants.gender import Gender

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestEmployeeModel:
    def test_employee_creation(self, employee_user):
        """Testa criação básica de um funcionário"""
        employee = Employee.objects.create(
            user=employee_user,
            first_name="Carlos",
            last_name="Mendes",
            username="carlosmendes",
            phone="11999998888",
            bio="Especialista em cabelos",
            gender=Gender.MALE,
            birth_date=date(1985, 5, 20),
            instagram="https://instagram.com/carlos.mendes"
        )
        
        assert employee.id is not None
        assert isinstance(employee.id, uuid.UUID)
        assert employee.user == employee_user
        assert employee.first_name == "Carlos"
        assert employee.last_name == "Mendes"
        assert employee.username == "carlosmendes"
        assert employee.phone == "11999998888"
        assert employee.bio == "Especialista em cabelos"
        assert employee.gender == Gender.MALE
        assert employee.birth_date == date(1985, 5, 20)
        assert employee.instagram == "https://instagram.com/carlos.mendes"
        assert str(employee) == "Carlos Mendes (employee@example.com)"

    def test_employee_str_method(self, employee_user):
        """Testa o método __str__ do Employee"""
        employee = Employee.objects.create(
            user=employee_user,
            first_name="Ana",
            last_name="Paula"
        )
        assert str(employee) == "Ana Paula (employee@example.com)"

    def test_employee_photo_url_with_default_photo(self, employee_user, monkeypatch):
        """Testa photo_url quando não há foto personalizada"""
        employee = Employee.objects.create(user=employee_user)
        
        # Mock CORRETO - função que aceita o parâmetro 'name'
        def mock_storage_url(name):  # ← CORRIGIDO: função recebe 'name', não 'self'
            return "/media/default/employee_img.jpeg"
        
        monkeypatch.setattr(employee.photo.storage, 'url', mock_storage_url)
        
        url = employee.photo_url
        assert url == "/media/default/employee_img.jpeg"

    def test_employee_photo_url_with_custom_photo(self, employee_user, monkeypatch):
        """Testa photo_url com foto personalizada"""
        employee = Employee.objects.create(
            user=employee_user,
            photo=SimpleUploadedFile("photo.jpg", b"file_content", content_type="image/jpeg")
        )
        
        def mock_url(self):
            return "/media/photos/photo.jpg"
        
        monkeypatch.setattr(type(employee.photo), 'url', property(mock_url))
        
        url = employee.photo_url
        assert url == "/media/photos/photo.jpg"

    def test_employee_photo_url_custom_photo_not_exists(self, employee_user, monkeypatch):
        """Testa photo_url quando foto personalizada não existe no bucket"""
        employee = Employee.objects.create(
            user=employee_user,
            photo=SimpleUploadedFile("photo.jpg", b"file_content", content_type="image/jpeg")
        )
        
        def mock_url_with_exception(self):
            raise Exception("File not found")
        
        # Mock CORRETO - função que aceita o parâmetro 'name'
        def mock_storage_url(name):  # ← CORRIGIDO: função recebe 'name', não 'self'
            return "/media/default/employee_img.jpeg"
        
        monkeypatch.setattr(type(employee.photo), 'url', property(mock_url_with_exception))
        monkeypatch.setattr(employee.photo.storage, 'url', mock_storage_url)
        
        url = employee.photo_url
        assert url == "/media/default/employee_img.jpeg"

    def test_employee_gender_label(self, employee_user):
        """Testa a property gender_label"""
        employee = Employee.objects.create(
            user=employee_user,
            gender=Gender.MALE
        )
        assert employee.gender_label == "Masculino"
        
        employee2 = Employee.objects.create(
            user=User.objects.create_user(email="employee2@example.com", password="pass123"),
            gender=Gender.FEMALE
        )
        assert employee2.gender_label == "Feminino"
        
        employee3 = Employee.objects.create(
            user=User.objects.create_user(email="employee3@example.com", password="pass123"),
            gender=Gender.OTHER
        )
        assert employee3.gender_label == "Outro"

    def test_employee_get_full_name(self, employee_user):
        """Testa o método get_full_name"""
        employee = Employee.objects.create(
            user=employee_user,
            first_name="Carlos",
            last_name="Mendes"
        )
        assert employee.get_full_name() == "Carlos Mendes"
        
        employee2 = Employee.objects.create(
            user=User.objects.create_user(email="emp2@example.com", password="pass123"),
            first_name="Ana"
        )
        assert employee2.get_full_name() == "Ana"
        
        employee3 = Employee.objects.create(
            user=User.objects.create_user(email="emp3@example.com", password="pass123"),
            last_name="Santos"
        )
        assert employee3.get_full_name() == "Santos"
        
        employee4 = Employee.objects.create(
            user=User.objects.create_user(email="emp4@example.com", password="pass123"),
            username="emp123"
        )
        assert employee4.get_full_name() == "emp123"
        
        employee5 = Employee.objects.create(
            user=User.objects.create_user(email="emp5@example.com", password="pass123")
        )
        assert employee5.get_full_name().startswith("Employee ")

    def test_employee_save_with_photo(self, employee_user):
        """Testa o método save com foto"""
        employee = Employee(
            user=employee_user,
            first_name="Carlos",
            photo=SimpleUploadedFile("photo.jpg", b"file_content", content_type="image/jpeg")
        )
        employee.save()
        
        assert employee.photo.name != "default/employee_img.jpeg"
        assert employee.photo.name.startswith("photos/")

    def test_employee_save_without_photo(self, employee_user):
        """Testa o método save sem foto - deve usar foto padrão"""
        employee = Employee(
            user=employee_user,
            first_name="Carlos",
            photo=None
        )
        employee.save()
        
        assert employee.photo.name == "default/employee_img.jpeg"

    def test_employee_meta_options(self):
        """Testa as opções Meta do Employee"""
        assert Employee._meta.verbose_name == "Funcionário"
        assert Employee._meta.verbose_name_plural == "Funcionários"
        assert Employee._meta.ordering == ["first_name", "last_name"]
        assert len(Employee._meta.indexes) == 1
        assert Employee._meta.indexes[0].fields == ["first_name", "last_name"]