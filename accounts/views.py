from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserRegistrationSerializer

class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {'message': 'User registered successfully.'},
            status=status.HTTP_201_CREATED
        )
