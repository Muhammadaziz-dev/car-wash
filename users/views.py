from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import CustomUser
from .serializers import UserSerializer
from .services import get_user_balance, create_user


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        username = request.data.get('username')
        phone_number = request.data.get('phone_number')
        user = create_user(username, phone_number)
        serializer = self.get_serializer(user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
