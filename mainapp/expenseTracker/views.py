
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
import spacy

pytesseract.pytesseract.tesseract_cmd = r"C:\Users\svmra\OneDrive\Documents\Programming\tessaract\tesseract.exe"

# Create your views here.
def expense_list(request):
    expense = Expense.objects.all()
    total_amount = sum(expense.price for expense in expense)
    return render(request, 'expenseTracker/page.html', {'expense': expense,
                                                        'total': total_amount})

def add_expense(request):
    ocr_data = None
    form=None

    if request.method == 'POST':
        if 'bill_image' in request.FILES:
            uploaded_file = request.FILES['bill_image']
            fs = FileSystemStorage()
            image_path = fs.save(uploaded_file.name, uploaded_file)
            image_full_path = os.path.join(settings.MEDIA_ROOT, image_path)

            preprocessed_image = preprocess_image(image_full_path)
            preprocessed_path = image_full_path.replace('.', '_preprocessed.')
            cv2.imwrite(preprocessed_path, preprocessed_image)

            extracted_text = pytesseract.image_to_string(preprocessed_image)
            total = extract_total_from_bill(extracted_text)
            name = extract_name(extracted_text)

            if total:
                if ',' in total:
                    total = total.replace(',', '')  
                price = float(total.strip())  
            else:
                price = 0.0

            ocr_data = {'title': name, 'price': price, 'category': 'other', 'note': 'Added through OCR'}
            form=ExpenseForm(initial=ocr_data)
            
            fs.delete(image_path)  
            fs.delete(image_full_path)
            fs.delete(preprocessed_path)
        else:
            form = ExpenseForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('expense_list')
    else:
        form = ExpenseForm(initial=ocr_data)

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


def preprocess_image(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    angle = cv2.minAreaRect(coords)[-1]
    
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC)
    
    return rotated

def extract_total_from_bill(results):
    price_patterns = [
        re.compile(r'\b\₹?\s*\d{1,3}(?:,\d{3})*\.\d{2}\b'), 
        re.compile(r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b')
    ]
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

def extract_name(result):

    nlp = spacy.load("en_core_web_sm")
    doc = nlp(result)

    potential_names=[ent.text for ent in doc.ents if ent.label_ in ["ORG"]]

    for line in result.split('\n')[:1]:  
        if any(name in line for name in potential_names):
            print(line)
            return line.strip()