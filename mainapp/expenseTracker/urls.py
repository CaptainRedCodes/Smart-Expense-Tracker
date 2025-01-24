from django.urls import path
from .views import add_expense,expense_list,delete_expense,update_expense,export_as_csv,export_as_pdf

urlpatterns=[
    path('',expense_list,name='expense_list'),
    path('add/',add_expense,name='add_expense'),
    path('delete/<int:expense_id>/', delete_expense, name='delete_expense'),
    path('edit/<int:expense_id>/', update_expense, name='update_expense'),
    path('export_csv/',export_as_csv,name='export_as_csv'),
    path('export_pdf/',export_as_pdf,name='export_as_pdf'),
]