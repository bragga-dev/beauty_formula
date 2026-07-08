from django.apps import AppConfig


class PaymentConfig(AppConfig):
    name = 'beauty_formula.apps.payment'
    label = 'payment'
    default_auto_field = 'django.db.models.BigAutoField'
    verbose_name = 'Pagamento'