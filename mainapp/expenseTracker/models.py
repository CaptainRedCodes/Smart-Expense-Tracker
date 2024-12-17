from django.db import models
from django.conf import settings

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
    title=models.CharField(max_length=50,blank=False)
    price=models.DecimalField(max_digits=6,decimal_places=2,blank=False)
    category=models.CharField(max_length=50,choices=CHOICES,default="Other")
    date=models.DateTimeField(auto_now_add=True,blank=False)
    note=models.TextField(max_length=50,blank=True,default="An Expense")


    class Meta:
        ordering = ('title','category','note','price','date')
