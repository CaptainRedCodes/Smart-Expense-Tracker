
import re
from django.shortcuts import get_object_or_404, render, redirect
from .models import Expense
from .forms import ExpenseForm
import pytesseract
from PIL import Image
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import cv2
import numpy as np


pytesseract.pytesseract.tesseract_cmd = r"C:\Users\svmra\OneDrive\Documents\Programming\tessaract\tesseract.exe"

# Create your views here.
def expense_list(request):
    expense = Expense.objects.all()
    total_amount = sum(expense.price for expense in expense)
    return render(request, 'expenseTracker/page.html', {'expense': expense,
                                                        'total': total_amount})

def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('expense_list')
    else:
        form = ExpenseForm()
    return render(request, 'expenseTracker/add.html', {'form': form})

def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    expense.delete()
    return redirect('expense_list')

def update_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect('expense_list')
    else:
        form = ExpenseForm()
    return render(request, 'expenseTracker/add.html', {'form': form})


# def preprocess_image(image_path):
#     # Read the image
#     image = cv2.imread(image_path)
    
#     # Convert to grayscale
#     gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
#     # Apply thresholding to preprocess the image
#     thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    
#     # Apply deskewing
#     coords = np.column_stack(np.where(thresh > 0))
#     angle = cv2.minAreaRect(coords)[-1]
    
#     # Rotate the image to correct skew
#     if angle < -45:
#         angle = -(90 + angle)
#     else:
#         angle = -angle
    
#     (h, w) = image.shape[:2]
#     center = (w // 2, h // 2)
#     M = cv2.getRotationMatrix2D(center, angle, 1.0)
#     rotated = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLACEOUTSIDE)
    
#     return rotated

def upload_bill(request):
    if request.method == 'POST' and 'bill_image' in request.FILES:

        uploaded_file = request.FILES['bill_image']
        fs = FileSystemStorage()
        image_path = fs.save(uploaded_file.name, uploaded_file)
        image_full_path = os.path.join(settings.MEDIA_ROOT, image_path)
        
            # preprocessed_image = preprocess_image(image_full_path)
            # preprocessed_path = image_full_path.replace('.', '_preprocessed.')
            # cv2.imwrite(preprocessed_path, preprocessed_image)
            
        extracted_text = pytesseract.image_to_string(image_full_path)
        total = extract_total_from_bill(extracted_text)

        expense_upload=Expense.objects.create(title='added through OCR',
                                              price=float(total.replace(',', '').strip()),
                                              category='other',
                                              note='Hello world',
                                              )
        expense_upload.save()
            
        fs.delete(image_path)
            
        return render(request, 'expenseTracker/upload.html', {
            'total_amount': total,
        })
    
    return render(request, 'expenseTracker/upload.html')

def extract_total_from_bill(results):
    
    price_patterns = [
        re.compile(r'\b\₹?\s*\d{1,3}(?:,\d{3})*\.\d{2}\b'), 
        re.compile(r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b')
    ]
    
    # Expanded total keywords
    total_keywords = [
        'total', 'grand total', 'amount due', 'balance',
        'total amount', 'net total', 'payable', 'to pay',
        'sub total', 'total due', 'sub totel', 'amount'
    ]
    
    
    lines = results.splitlines()
    for line in lines:
        line_lower = line.lower()
        
        
        if any(keyword in line_lower for keyword in total_keywords):
            for pattern in price_patterns:
                match = pattern.search(line_lower)
                if match:
                
                    return match.group(0).replace('₹', '').strip()
    
    return None

