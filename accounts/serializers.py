from rest_framework import serializers
from .models import CustomUser

class UserRegistrationSerializer(serializers.ModelSerializer):
    # Create two write-only fields for password input
    password1 = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'role', 'password1', 'password2')

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        # Remove the confirmation password
        password = validated_data.pop('password1')
        validated_data.pop('password2')
        # Use the custom manager to create the user (this handles password hashing)
        user = CustomUser.objects.create_user(password=password, **validated_data)
        return user
