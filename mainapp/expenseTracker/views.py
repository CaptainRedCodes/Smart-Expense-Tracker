import re
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .models import Expense
from .forms import ExpenseForm
import pytesseract
import os
import cv2
from collections import defaultdict
import datetime
from groq import Groq
from django.conf import settings
from django.contrib import messages 
import csv
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import io


# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\svmra\OneDrive\Documents\Programming\tessaract\tesseract.exe"

client=Groq(api_key=settings.GROQ_API_KEY)


@login_required
def expense_list(request):

    """Display list of expenses, total amount, and graph for logged-in user."""
    expenses = request.user.expenses.all()
    total_amount = sum(expense.price for expense in expenses)
    
    total_data = defaultdict(float)
    month_data = defaultdict(float)
    
    current_month = datetime.datetime.now().month
    current_year = datetime.datetime.now().year

    for exp in expenses:
    
        exp_month = exp.date.month
        exp_year = exp.date.year

        if exp_month == current_month:
            month_data[exp.category] += float(exp.price)
        total_data[exp.category] += float(exp.price)

    
    # Render the template with the pie charts and data
    return render(request, 'expenseTracker/page.html', {
        'expense': expenses,
        'total':total_amount,
    })

@login_required
def add_expense(request):
    """Add new expense with optional OCR bill processing."""
    # Debug information
    form = None
    ocr_data = None
    
    try:
        if request.method == 'POST':
            if 'bill_image' in request.FILES:
                uploaded_file = request.FILES['bill_image']
                fs = FileSystemStorage()
                image_path = None
                image_full_path = None
                preprocessed_path = None
                
                try:
                    # Create upload directory if it doesn't exist
                    upload_dir = os.path.join(settings.MEDIA_ROOT, 'bills', str(request.user.id))
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Save and process the image
                    filename = f"{request.user.id}_{uploaded_file.name}"
                    image_path = fs.save(os.path.join('bills', str(request.user.id), filename), uploaded_file)
                    image_full_path = os.path.join(settings.MEDIA_ROOT, image_path)
                    
                    # Process image
                    preprocessed_image = preprocess_image(image_full_path)
                    preprocessed_path = os.path.join(upload_dir, f'preprocessed_{filename}')
                    cv2.imwrite(preprocessed_path, preprocessed_image)
                    
                    # Extract text
                    extracted_text = pytesseract.image_to_string(preprocessed_image)
                    print(f"Extracted text: {extracted_text}")
                    
                    # Process the text
                    total = extract_total_from_bill(extracted_text)
                    name = extract_name(extracted_text) 
                    
                    if total:
                        try:
                            total = float(total)
                        except (ValueError, TypeError):
                            total = 0.0
                            messages.warning(request, "Could not parse total amount from bill")
                    
                    # Create form with extracted data
                    ocr_data = {
                        'title': name[:15] if name else 'Bill Upload',
                        'price': total if total else 0.0,
                        'category': 'other',
                        'note': f'OCR Extracted Text{name[15:]}'
                    }
                    form = ExpenseForm(initial=ocr_data)
                    messages.success(request, "Bill processed successfully")
                    
                except Exception as e:
                    print(f"Error processing image: {str(e)}")
                    messages.error(request, f"Error processing image: {str(e)}")
                    form = ExpenseForm()
                
                finally:
                    # Cleanup files
                    try:
                        if image_path and fs.exists(image_path):
                            fs.delete(image_path)
                        if image_full_path and os.path.exists(image_full_path):
                            os.remove(image_full_path)
                        if preprocessed_path and os.path.exists(preprocessed_path):
                            os.remove(preprocessed_path)
                    except Exception as e:
                        print(f"Error cleaning up files: {str(e)}")
            
            else:
                # Handle manual form submission
                form = ExpenseForm(request.POST)
                if form.is_valid():
                    expense = form.save(commit=False)
                    expense.user = request.user
                    expense.save()
                    messages.success(request, "Expense added successfully")
                    return redirect('expense_list')
                else:
                    messages.error(request, "Please correct the errors below")
        
        else:
            form = ExpenseForm()
        
        return render(request, 'expenseTracker/add.html', {
            'form': form,
            'ocr_data': ocr_data
        })
        
    except Exception as e:
        print(f"View error: {str(e)}")
        messages.error(request, "An error occurred while processing your request")
        return render(request, 'expenseTracker/add.html', {
            'form': ExpenseForm(),
            'error': str(e)
        })

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
def export_as_pdf(request):
    """Export the expenses data through pdf."""

    expenses = Expense.objects.filter(user=request.user)
    data = [['Title', 'Amount', 'Category', 'Date']]  # Fixed header row
    for item in expenses:
        data.append([
            item.title, 
            item.price, 
            item.category,
            item.date,
        ])

    # Create an in-memory file buffer
    buffer = io.BytesIO()

    # Create PDF document
    doc = SimpleDocTemplate(buffer)
    
    # Create table
    table = Table(data)

    # Add table style
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table.setStyle(style)

    # Build PDF
    elements = [table]
    doc.build(elements)

    # Get the PDF content from the buffer
    buffer.seek(0)

    # Create response
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=expenses_{request.user}.pdf'

    # Close the buffer
    buffer.close()

    return response


def export_as_csv(request):

    response=HttpResponse(content_type='text/csv')
    response['Content-Disposition']='attachment; filename=Expenses'+str(request.user)+ str(datetime.datetime.now()) +'.csv'
    
    writer=csv.writer(response)
    writer.writerow(['Title''Amount','Category','Date'])

    expenses=Expense.objects.filter(user=request.user)

    for expense in expenses:
        writer.writerow([expense.title,expense.price,expense.category,expense.date])

    return response



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



def extract_total_from_bill(results):
    """Extract total amount from OCR results using Ai."""

    prompt=f''''Assuming yourself as a finanacial evaluator and extract the total bill amount from the bill with taxes included(just give float value of the bill): {results}.'''
    print('Contacting Groq')

    try:
        completion=client.chat.completions.create(
        messages=[{
                "role": "user",
                "content": prompt,
        }],
            model="llama-3.3-70b-versatile",
            stream=False,
        )

        response = completion.choices[0].message.content
        
        print(response)
        try:
            amount=float(response)
            return amount
        except ValueError:
            print("Could not convert the amount to float")
            return None

    except Exception as e:
        print(f"Error{str(e)}")
        return None



def extract_name(results):
    """Extract name from OCR results using Ai."""

    prompt=f''' "Extract the first 20 characters from the text as the restaurant name, without any interpretation.
    Then, provide a concise description of the context based on the remaining text.
     Do not speculate or explain beyond what is provided.
    Text: {results}"
    
    Desired Output Format:

    [First 20 characters of restaurant name]
    Description: [Relevant context from the text] '''

    print('Contacting Groq')
    try:
        completion=client.chat.completions.create(
        messages=[{
                "role": "user",
                "content": prompt,
        }],
            model="llama-3.3-70b-versatile",
            stream=False,
        )

        response = completion.choices[0].message.content
       
        print(f"response is : {response}")
        try:
            return response
        except ValueError:
            print("Could not get any name or information")
            return None

    except Exception as e:
        print(f"Error{str(e)}")
        return None
