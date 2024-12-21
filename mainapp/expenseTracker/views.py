import re
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .models import Expense
from .forms import ExpenseForm
import pytesseract
from PIL import Image
import os
import cv2
import numpy as np
import spacy
import plotly.express as px
from collections import defaultdict
from datetime import datetime

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\svmra\OneDrive\Documents\Programming\tessaract\tesseract.exe"

def home(request):
    """Render the homepage."""
    return render(request, 'expenseTracker/homepage.html')

@login_required
def expense_list(request):

    """Display list of expenses, total amount, and graph for logged-in user."""
    
    expense = request.user.expenses.all()
    total_amount = sum(expense.price for expense in expense)
    
    total_data = defaultdict(float)
    month_data = defaultdict(float)
    
    current_month = datetime.now().month
    current_year = datetime.now().year

    for exp in expense:
    
        exp_month = exp.date.month
        exp_year = exp.date.year

        if exp_month == current_month:
            month_data[exp.category] += float(exp.price)
        total_data[exp.category] += float(exp.price)

    mfig = px.pie(
        values=list(month_data.values()),
        names=list(month_data.keys()),
        template='plotly_white',
    )

    mfig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='white'
    )
    
    mfig.update_traces(
         hovertemplate="Category: %{label}<br>Amount: %{value:.2f}<br>Percentage: %{percent}<extra></extra>",
         textinfo='percent+label'
    )

    yfig = px.pie(
        values=list(total_data.values()),
        names=list(total_data.keys()),
        template='plotly_white',
    )

    yfig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='white'
    )
    
    yfig.update_traces(
         hovertemplate="Category: %{label}<br>Amount: %{value:.2f}<br>Percentage: %{percent}<extra></extra>",
         textinfo='percent+label'
    )
    
    month_chart = mfig.to_html(full_html=False, include_plotlyjs=True)
    year_chart = yfig.to_html(full_html=False, include_plotlyjs=True)
    
    # Render the template with the pie charts and data
    return render(request, 'expenseTracker/page.html', {
        'expense': expense,
        'total':total_amount,
        'month_chart': month_chart,
        'year_chart': year_chart
    })

@login_required
def add_expense(request):
    """Add new expense with optional OCR bill processing."""
    ocr_data = None
    form = None

    if request.method == 'POST':
        if 'bill_image' in request.FILES:
            # Handle bill image upload and OCR processing
            uploaded_file = request.FILES['bill_image']
            fs = FileSystemStorage()
            image_path = fs.save(uploaded_file.name, uploaded_file)
            image_full_path = os.path.join(settings.MEDIA_ROOT, image_path)

            # Preprocess and extract information from image
            preprocessed_image = preprocess_image(image_full_path)
            preprocessed_path = image_full_path.replace('.', '_preprocessed.')
            cv2.imwrite(preprocessed_path, preprocessed_image)

            extracted_text = pytesseract.image_to_string(preprocessed_image)
            total = extract_total_from_bill(extracted_text)
            name = extract_name(extracted_text)

            # Process extracted total amount
            if total:
                if ',' in total:
                    total = total.replace(',', '')
                price = float(total.strip())
            else:
                price = 0.0

            ocr_data = {
                'title': name,
                'price': price,
                'category': 'other',
                'note': 'Added through OCR'
            }
            form = ExpenseForm(initial=ocr_data)
            
            # Cleanup temporary files
            fs.delete(image_path)
            fs.delete(image_full_path)
            fs.delete(preprocessed_path)
        else:
            # Handle manual form submission
            form = ExpenseForm(request.POST)
            if form.is_valid():
                expense = form.save(commit=False)
                expense.user = request.user
                expense.save()
                return redirect('expense_list')
    else:
        form = ExpenseForm(initial=ocr_data)

    return render(request, 'expenseTracker/add.html', {'form': form})

@login_required
def delete_expense(request, expense_id):
    """Delete an expense entry."""
    expense = get_object_or_404(Expense, id=expense_id)
    expense.delete()
    return redirect('expense_list')

@login_required
def update_expense(request, expense_id):
    """Update an existing expense entry."""
    expense = get_object_or_404(Expense, id=expense_id)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect('expense_list')
    else:
        form = ExpenseForm()
    return render(request, 'expenseTracker/add.html', {'form': form})

@login_required
def preprocess_image(image_path):
    """Preprocess bill image for better OCR results."""
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding and rotation correction
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    angle = cv2.minAreaRect(coords)[-1]
    
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    # Rotate image to correct orientation
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC)
    
    return rotated

@login_required
def extract_total_from_bill(results):
    """Extract total amount from OCR results using regex patterns."""
    price_patterns = [
        re.compile(r'\b\₹?\s*\d{1,3}(?:,\d{3})*\.\d{2}\b'),
        re.compile(r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b')
    ]
    total_keywords = [
        'total', 'grand total', 'amount due', 'balance',
        'total amount', 'net total', 'payable', 'to pay',
        'sub total', 'total due', 'sub totel', 'amount', '₹', 'price'
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

@login_required
def extract_name(result):
    """Extract organization name from OCR results using spaCy NER."""
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(result)

    potential_names = [ent.text for ent in doc.ents if ent.label_ == "ORG"]

    for line in result.split('\n')[:1]:
        if any(name in line for name in potential_names):
            return line.strip()
    return None

