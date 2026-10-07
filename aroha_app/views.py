from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import HelpRequestForm, SignUpForm
from .models import HelpRequest


# ==========================================
# Authentication & Access Views
# ==========================================

def signup(request):
    """Handles user registration for volunteers and requesters."""
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            "Account created! Please wait for an admin to approve it, then you can log in.",
        )
        return redirect("login")
    return render(request, "registration/signup.html", {"form": form})


@login_required
def dashboard_redirect(request):
    user = request.user
    if user.role == user.Role.REQUESTER:
        return redirect("request_list")
    elif user.role == user.Role.STAFF:
        return redirect("barangay_request_list") # Redirects staff straight to request_list_2.html
    elif user.role == user.Role.VOLUNTEER:
        return redirect("volunteer_list")
    elif user.role == user.Role.ADMIN or user.is_superuser:
        return redirect("admin_dashboard")

    return redirect("request_list")

# ==========================================
# Requester Views
# ==========================================

@login_required
def request_list(request):
    """Displays active requests (Pending or In Progress) for the logged-in requester."""
    requests = HelpRequest.objects.filter(
        requester=request.user,
        status__in=[HelpRequest.Status.PENDING, HelpRequest.Status.IN_PROGRESS],
    )
    return render(request, "requester/request_list.html", {"requests": requests})


@login_required
def request_history(request):
    """Displays completed or rejected requests for the logged-in requester."""
    requests = HelpRequest.objects.filter(
        requester=request.user,
        status__in=[HelpRequest.Status.COMPLETED, HelpRequest.Status.REJECTED],
    )
    return render(request, "requester/request_history.html", {"requests": requests})


@login_required
def request_create(request):
    """Handles creating a new help request."""
    if request.method == "POST":
        form = HelpRequestForm(request.POST)
        if form.is_valid():
            help_request = form.save(commit=False)
            help_request.requester = request.user
            help_request.save()
            messages.success(request, "Your request has been submitted successfully.")
            return redirect("request_list")
    else:
        form = HelpRequestForm()
    return render(request, "requester/request_form.html", {"form": form})


@login_required
def request_edit(request, pk):
    """Handles editing an existing pending request."""
    help_request = get_object_or_404(HelpRequest, pk=pk, requester=request.user)

    # Prevent editing requests that are already in progress, completed, or rejected
    if help_request.status != HelpRequest.Status.PENDING:
        messages.error(request, "You can only edit pending requests.")
        return redirect("request_list")

    if request.method == "POST":
        form = HelpRequestForm(request.POST, instance=help_request)
        if form.is_valid():
            form.save()
            messages.success(request, "Request updated successfully.")
            return redirect("request_list")
    else:
        form = HelpRequestForm(instance=help_request)

    return render(
        request, "requester/request_form.html", {"form": form, "object": help_request}
    )

@login_required
def profile_preview(request, role="family-member"):
    user = request.user
    
    # Map role parameter or actual user role
    context = {
        "account_type": role,
        "role_label": "Family member" if role == "family-member" else role.capitalize(),
        "display_name": user.get_full_name() or user.username,
        "username": user.username,
        "phone_number": getattr(user, "phone_number", "Not provided"),
    }
    return render(request, "profile_preview.html", context)

from .forms import BarangayStatusForm, HelpRequestForm, SignUpForm
from .models import HelpRequest

# ==========================================
# Barangay Staff Views
# ==========================================

@login_required
def barangay_request_list(request):
    """Displays all help requests for Barangay Staff review."""
    requests = HelpRequest.objects.all().order_by("-created_at")
    return render(request, "barangay/request_list.html", {"requests": requests})


@login_required
def barangay_request_detail(request, pk):
    """View details of a single request and update its status."""
    help_request = get_object_or_404(HelpRequest, pk=pk)

    if request.method == "POST":
        form = BarangayStatusForm(request.POST, instance=help_request)
        if form.is_valid():
            form.save()
            messages.success(request, "Request status updated successfully.")
            return redirect("barangay_request_list")
    else:
        form = BarangayStatusForm(instance=help_request)

    return render(
        request,
        "barangay/request_detail.html",
        {"object": help_request, "form": form},
    )