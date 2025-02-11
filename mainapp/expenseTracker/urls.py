from django.urls import path
from .views import ExpenseAPIView, ExpenseOCRView, ExpenseExportView

urlpatterns = [
    # Base expense CRUD endpoints
    path('expenses/', ExpenseAPIView.as_view(), name='expense-list-create'),
    path('expenses/<int:pk>/', ExpenseAPIView.as_view(), name='expense-detail'),
    
    # OCR processing endpoint
    path('expenses/ocr/', ExpenseOCRView.as_view(), name='expense-ocr'),
    
    # Export endpoints
    path('expenses/export/', ExpenseExportView.as_view(), name='expense-export'),
]