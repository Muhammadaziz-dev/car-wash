from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Payment
from .serializers import PaymentSerializer
from .services import create_payment, update_balance
from users.models import CustomUser


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def create(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        method = request.data.get('method')
        amount = float(request.data.get('amount'))

        user = CustomUser.objects.get(id=user_id)
        payment = create_payment(user, method, amount)
        update_balance(user, amount)

        serializer = self.get_serializer(payment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
