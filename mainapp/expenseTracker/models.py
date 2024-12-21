from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
CHOICES=(
        ('Food', 'Food'),
        ('Travel', 'Travel'),
        ('Shopping', 'Shopping'),
        ('Utilities', 'Utilities'),
        ('Health', 'Health'),
        ('Education', 'Education'),
        ('Other', 'Other')
)
# Create your models here.
class Expense(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='expenses',
        null=True,
        blank=True
    )
    title=models.CharField(max_length=50,blank=False)
    price=models.DecimalField(max_digits=10,decimal_places=2,blank=False)
    category=models.CharField(max_length=50,choices=CHOICES,default="Other")
    date=models.DateTimeField(auto_now_add=True,blank=False)
    note=models.TextField(max_length=50,blank=True,default="An Expense")


    class Meta:
        ordering = ['-date']

class UserProfile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='expense_profile'  
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Expense Profile"