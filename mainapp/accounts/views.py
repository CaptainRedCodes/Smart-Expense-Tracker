
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login,authenticate
from django.shortcuts import redirect
from expenseTracker.models import Expense
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import render
# Define a view function for the home page


def login_page(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not User.objects.filter(username=username).exists():
            messages.error(request, 'Invalid Username')
            return redirect('/accounts/login')
        
        user = authenticate(username=username, password=password)
        
        if user is None:
            messages.error(request, "Invalid Password")
            return redirect('/accounts/login')
        else:
            login(request, user)
            return redirect('dashboard')
    
    return render(request, 'accounts/login.html')


def register_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = User.objects.filter(username=username)
        
        if user.exists():
            messages.info(request, "Username already taken!")
            return redirect('/register/')
        
        user = User.objects.create_user(
            username=username
        )
        
        user.set_password(password)
        user.save()
        
        messages.info(request, "Account created Successfully!")
        return redirect('login')
    
    return render(request, 'accounts/signup.html')

@login_required
def account_dashboard(request):
        return render(request,'accounts/landing.html')