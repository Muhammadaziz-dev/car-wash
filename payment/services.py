from .models import Payment
from users.models import CustomUser

def create_payment(user: CustomUser, method: str, amount: float) -> Payment:
    """Creates a payment entry."""
    return Payment.objects.create(user=user, method=method, amount=amount)

def update_balance(user: CustomUser, amount: float) -> None:
    """Updates user balance after payment."""
    user.balance += amount
    user.save()
