from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class Device(models.Model):
    STATUS_CHOICES = (
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('maintenance', 'Under Maintenance'),
        ('error', 'Error'),
        ('disabled', 'Disabled'),
    )
    REGISTRATION_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )

    name = models.CharField(max_length=100)
    device_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')
    ip_address = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)
    port = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(65535)])
    location = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    registration_status = models.CharField(max_length=20, choices=REGISTRATION_STATUS_CHOICES, default='pending')
    registration_message = models.TextField(blank=True)
    last_handshake_attempt = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.device_id})"

class WashProgram(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price_per_minute = models.DecimalField(max_digits=10, blank=True, null=True, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    price_per_second = models.DecimalField(max_digits=10, decimal_places=2,
                                           validators=[MinValueValidator(Decimal('0.01'))], default=Decimal('0.16667'))
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class DeviceConfiguration(models.Model):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='configuration')
    
    # Pricing settings
    price_per_minute = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))], 
        help_text="Base price per minute"
    )
    
    # Timer settings
    default_timeout = models.PositiveIntegerField(
        default=300,
        help_text="Default timeout in seconds"
    )
    
    # Bonus settings
    bonus_duration_enabled = models.BooleanField(default=False)
    bonus_duration_amount = models.PositiveIntegerField(
        default=0,
        help_text="Additional bonus time in seconds"
    )
    
    # Valve reset settings
    valve_reset_timeout = models.PositiveIntegerField(
        default=60,
        help_text="Valve reset timeout in seconds"
    )
    
    # Program specific settings
    custom_programs = models.ManyToManyField(WashProgram, through='DeviceProgramSetting')
    
    # Template name (if this is a template configuration)
    is_template = models.BooleanField(default=False)
    template_name = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Add these fields to DeviceConfiguration model
    engine_performance = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    pump_performance = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    def __str__(self):
        if self.is_template:
            return f"Template: {self.template_name}"
        return f"Config for {self.device.name}"

class DeviceProgramSetting(models.Model):
    device_config = models.ForeignKey(DeviceConfiguration, on_delete=models.CASCADE)
    program = models.ForeignKey(WashProgram, on_delete=models.CASCADE)
    custom_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        null=True,
        blank=True
    )
    is_enabled = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('device_config', 'program')
    
    def __str__(self):
        return f"{self.program.name} for {self.device_config}"

class DeviceLog(models.Model):
    LOG_TYPES = (
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('command', 'Command'),
        ('status_change', 'Status Change'),
    )
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='logs')
    log_type = models.CharField(max_length=20, choices=LOG_TYPES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_log_type_display()}: {self.device.name} - {self.created_at}"

class DeviceSession(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('error', 'Error'),
        ('cancelled', 'Cancelled'),
    )
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    total_duration = models.PositiveIntegerField(default=0, help_text="Total duration in seconds")
    program = models.ForeignKey(WashProgram, on_delete=models.SET_NULL, null=True, related_name='sessions')
    client_card = models.CharField(max_length=50, blank=True, null=True)
    amount_charged = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    bonus_time_used = models.PositiveIntegerField(default=0, help_text="Bonus time used in seconds")
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Session {self.id} - {self.device.name} - {self.started_at}"
