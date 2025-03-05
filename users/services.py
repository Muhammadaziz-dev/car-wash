from .models import CustomUser


def create_user(username: str, phone_number: str = None) -> CustomUser:
    return CustomUser.objects.create(username=username, phone_number=phone_number)


def get_user_balance(user_id: int) -> float:
    user = CustomUser.objects.get(id=user_id)
    return float(user.balance)