from django.urls import path
from .views import add_expense,expense_list,delete_expense,update_expense

urlpatterns=[
    path('page/',expense_list,name='expense_list'),
    path('add/',add_expense,name='add_expense'),
    path('delete/<int:expense_id>/', delete_expense, name='delete_expense'),
    path('edit/<int:expense_id>/', update_expense, name='update_expense'),
    
]