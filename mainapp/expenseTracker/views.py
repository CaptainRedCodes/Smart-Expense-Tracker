from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import status
import pytesseract
import cv2
import numpy as np
import io
import csv
from datetime import datetime
from collections import defaultdict
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from django.http import HttpResponse
from groq import Groq
from .models import Expense
from .serializers import ExpenseSerializer

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\svmra\OneDrive\Documents\Programming\tessaract\tesseract.exe"

class ExpenseAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class=ExpenseSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request):
        """Get all expenses with analytics"""
        expenses = request.user.expenses.all()
        total_amount = sum(expense.price for expense in expenses)
        
        total_data = defaultdict(float)
        month_data = defaultdict(float)
        current_month = datetime.now().month
        
        for exp in expenses:
            if exp.date.month == current_month:
                month_data[exp.category] += float(exp.price)
            total_data[exp.category] += float(exp.price)
        
        return Response({
            'expenses': ExpenseSerializer(expenses, many=True).data,
            'total': total_amount,
            'monthly_data': dict(month_data),
            'total_data': dict(total_data)
        })

    def post(self, request):
        """Add new expense"""
        serializer = ExpenseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """Update expense"""
        try:
            expense = Expense.objects.get(pk=pk, user=request.user)
        except Expense.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
            
        serializer = ExpenseSerializer(expense, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Delete expense"""
        try:
            expense = Expense.objects.get(pk=pk, user=request.user)
        except Expense.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
            
        expense.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ExpenseOCRView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def preprocess_image(self, image):
        """Preprocess bill image for better OCR results"""
        # Convert uploaded file to opencv format
        nparr = np.frombuffer(image.read(), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        coords = np.column_stack(np.where(thresh > 0))
        angle = cv2.minAreaRect(coords)[-1]
        
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC)
        
        return rotated

    def extract_total_from_bill(self, results):
        """Extract total amount using Groq AI"""
        client = Groq()
        prompt = f"Assuming yourself as a financial evaluator and extract the total bill amount from the bill with taxes included(just give float value of the bill): {results}"
        
        try:
            completion = client.chat.completions.create(
                messages=[{
                    "role": "user",
                    "content": prompt,
                }],
                model="llama-3.3-70b-versatile",
                stream=False,
            )
            response = completion.choices[0].message.content
            return float(response)
        except Exception as e:
            return None

    def extract_name(self, results):
        """Extract vendor name using Groq AI"""
        client = Groq()
        prompt = f'''Extract the first 20 characters from the text as the restaurant name, without any interpretation.
        Then, provide a concise description of the context based on the remaining text.
        Text: {results}'''
        
        try:
            completion = client.chat.completions.create(
                messages=[{
                    "role": "user",
                    "content": prompt,
                }],
                model="llama-3.3-70b-versatile",
                stream=False,
            )
            return completion.choices[0].message.content
        except Exception as e:
            return None

    def post(self, request,*args,**kwargs):
        """Process bill image and extract information"""
        if 'image' not in request.FILES:
            return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
            
        image = request.FILES['image']
        processed_image = self.preprocess_image(image)
        
        # Extract text using OCR
        text = pytesseract.image_to_string(processed_image)
        
        # Extract information
        total_amount = self.extract_total_from_bill(text)
        vendor_info = self.extract_name(text)
        
        return Response({
            'total_amount': total_amount,
            'vendor_info': vendor_info,
            'raw_text': text
        })

class ExpenseExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get_expense_data(self):
        """Get expense data for export"""
        expenses = self.request.user.expenses.all()
        return [['Title', 'Amount', 'Category', 'Date']] + [
            [expense.title, expense.price, expense.category, expense.date]
            for expense in expenses
        ]

    def get(self, request, format=None):
        """Export expenses in requested format"""
        export_format = request.query_params.get('format', 'csv')
        data = self.get_expense_data()
        
        if export_format == 'pdf':
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            table = Table(data)
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
            doc.build([table])
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename=expenses_{request.user}.pdf'
            return response
            
        else:  # CSV format
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename=Expenses_{request.user}_{datetime.now()}.csv'
            writer = csv.writer(response)
            writer.writerows(data)
            return response