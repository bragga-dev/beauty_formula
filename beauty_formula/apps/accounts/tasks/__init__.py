from beauty_formula.apps.accounts.tasks.verification_account import send_verification_email
from beauty_formula.apps.accounts.tasks.password_reset import send_password_reset_email
from beauty_formula.apps.accounts.tasks.send_promote_employee import send_promote_employee
from beauty_formula.apps.accounts.tasks.send_verification_email_employee import send_verification_email_employee
from beauty_formula.apps.accounts.tasks.send_verification_email_manager import send_verification_email_manager
from beauty_formula.apps.accounts.tasks.purge_unverified_accounts import purge_unverified_accounts_task


__all__ = [
    "send_verification_email",
    "send_password_reset_email",
    "send_promote_employee",
    "send_verification_email_employee",
    "send_verification_email_manager",
    "purge_unverified_accounts_task",
]