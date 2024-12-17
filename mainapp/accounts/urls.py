from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns=[
    path('login/',views.login_page,name='login'),
    path('logout/',LogoutView.as_view(next_page='login'),name='logout'),
    path('register/',views.register_page,name='register'),
    path('dashboard/', views.account_dashboard, name='dashboard'),
]