"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from aroha_app import views
from aroha_app.forms import ApprovedAuthenticationForm

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "login/",
        auth_views.LoginView.as_view(authentication_form=ApprovedAuthenticationForm),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),

    # Role Dispatcher
    path("dashboard/", views.dashboard_redirect, name="dashboard_redirect"),

    # Requester Views
    path("requests/", views.request_list, name="request_list"),
    path("requests/history/", views.request_history, name="request_history"),
    path("requests/new/", views.request_create, name="request_create"),
    path("requests/<int:pk>/edit/", views.request_edit, name="request_edit"),

    # Barangay Staff Views
    path("barangay/requests/", views.barangay_request_list, name="barangay_request_list"),
    path("barangay/requests/<int:pk>/", views.barangay_request_detail, name="barangay_request_detail"),

    # Profile View
    path("profile/<str:role>/", views.profile_preview, name="profile_preview"),
]