import random

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    ApprovedAuthenticationForm,
    BarangayStatusForm,
    HelpRequestForm,
    SignUpForm,
    VolunteerFeedbackForm,
)
from .models import HelpRequest, User


# ==========================================
# Shared, Core & Authentication Views
# ==========================================

def homepage(request):
    """Render the public Aroha landing page."""
    return render(request, "landing.html")


class CustomLoginView(LoginView):
    authentication_form = ApprovedAuthenticationForm

    def form_valid(self, form):
        user = form.get_user()
        
        # Check if user activated OTP in profile or is a superuser
        if user.is_otp_enabled or user.is_superuser:
            otp_code = str(random.randint(100000, 999999))
            
            # Store temporary authentication state in session
            self.request.session['pre_otp_user_id'] = user.id
            self.request.session['admin_otp'] = otp_code
            
            # Send verification email
            send_mail(
                subject='Aroha Security Verification Code',
                message=f'Your login verification code is: {otp_code}',
                from_email='noreply@aroha.com',
                recipient_list=[user.email],
                fail_silently=False,
            )
            return redirect('verify_otp')

        # Proceed with normal login if OTP is OFF
        return super().form_valid(form)


def verify_otp_view(request):
    user_id = request.session.get('pre_otp_user_id')
    stored_otp = request.session.get('admin_otp')

    # Direct access block without prior credentials validation
    if not user_id or not stored_otp:
        return redirect('login')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp_code', '').strip()

        if entered_otp == str(stored_otp):
            user = User.objects.get(id=user_id)
            login(request, user)
            
            del request.session['pre_otp_user_id']
            del request.session['admin_otp']

            if user.role == User.Role.VOLUNTEER:
                return redirect('volunteer_list')
            elif user.role == User.Role.REQUESTER:
                return redirect('request_list')
            elif user.is_staff or user.is_superuser:
                return redirect('barangay_request_list')
            return redirect('homepage')
        else:
            messages.error(request, 'Invalid verification code. Please try again.')

    return render(request, 'registration/verify_otp.html')


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
        return redirect("barangay_request_list")
    elif user.role == user.Role.VOLUNTEER:
        return redirect("volunteer_list")
    elif user.role == user.Role.ADMIN or user.is_superuser:
        return redirect("admin_panel")

    return redirect("request_list")


@login_required
def profile_preview(request, role="family-member"):
    user = request.user

    if request.method == "POST":
        user.is_otp_enabled = "is_otp_enabled" in request.POST
        user.save()
        return redirect("profile_preview", role=role)

    context = {
        "account_type": role,
        "role_label": "Family member" if role == "family-member" else role.capitalize(),
        "display_name": user.get_full_name() or user.username,
        "username": user.username,
        "email": user.email or "Not provided",
        "phone_number": getattr(user, "phone_number", "Not provided"),
        "is_otp_enabled": user.is_otp_enabled,
    }
    return render(request, "profile_preview.html", context)


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
def submit_volunteer_feedback(request, pk):
    help_request = get_object_or_404(
        HelpRequest,
        pk=pk,
        requester=request.user,
        status=HelpRequest.Status.COMPLETED,
    )
    if not help_request.assigned_volunteer:
        messages.error(request, "This request has no assigned volunteer to evaluate.")
        return redirect("request_history")
    if request.method == "POST":
        form = VolunteerFeedbackForm(request.POST, instance=help_request)
        if form.is_valid():
            form.save()
            messages.success(request, "Your volunteer feedback has been saved.")
    return redirect("request_history")


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
    """Handles editing an existing pending or in-progress request."""
    help_request = get_object_or_404(HelpRequest, pk=pk, requester=request.user)

    if help_request.status not in [HelpRequest.Status.PENDING, HelpRequest.Status.IN_PROGRESS]:
        messages.error(request, "You can only edit pending or in-progress requests.")
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
def request_delete(request, pk):
    """Allow a family member to delete their own request."""
    help_request = get_object_or_404(
        HelpRequest,
        pk=pk,
        requester=request.user,
        status__in=[HelpRequest.Status.PENDING, HelpRequest.Status.IN_PROGRESS],
    )
    if request.method == "POST":
        help_request.delete()
        messages.success(request, "Your request was deleted.")
    return redirect("request_list")


@login_required
def request_mark_complete(request, pk):
    """Let the family member confirm that an in-progress request is complete."""
    help_request = get_object_or_404(
        HelpRequest,
        pk=pk,
        requester=request.user,
        status__in=[HelpRequest.Status.PENDING, HelpRequest.Status.IN_PROGRESS],
    )
    if request.method == "POST":
        help_request.status = HelpRequest.Status.COMPLETED
        help_request.save(update_fields=["status", "updated_at"])
        if help_request.assigned_volunteer:
            messages.success(request, "Request marked as completed. You can rate your volunteer in request history.")
        else:
            messages.success(request, "Request marked as completed.")
    return redirect("request_list")


# ==========================================
# Barangay Staff Views
# ==========================================

@login_required
def barangay_request_list(request):
    """Displays filterable and sortable help requests for barangay staff."""
    requests = HelpRequest.objects.all()

    req_type = request.GET.get("request_type")
    barangay = request.GET.get("barangay")
    sort_order = request.GET.get("sort", "latest")

    if req_type:
        requests = requests.filter(request_type=req_type)
    if barangay:
        requests = requests.filter(barangay__iexact=barangay)

    if sort_order == "earliest":
        requests = requests.order_by("created_at")
    else:
        requests = requests.order_by("-created_at")

    available_barangays = (
        HelpRequest.objects.exclude(barangay__isnull=True)
        .exclude(barangay="")
        .values_list("barangay", flat=True)
        .distinct()
        .order_by("barangay")
    )

    context = {
        "requests": requests,
        "available_barangays": available_barangays,
        "request_types": HelpRequest.RequestType.choices,
        "active_type": req_type,
        "active_barangay": barangay,
        "active_sort": sort_order,
    }
    return render(request, "barangay/request_list.html", context)


@login_required
def barangay_ratings(request):
    """Show completed requests and volunteer ratings to barangay staff."""
    if not (request.user.is_superuser or request.user.role in ["staff", "admin"]):
        messages.error(request, "You do not have permission to view ratings.")
        return redirect("dashboard_redirect")

    completed = HelpRequest.objects.filter(status=HelpRequest.Status.COMPLETED).select_related(
        "requester", "assigned_volunteer"
    )
    account = request.GET.get("account", "")
    if account.startswith("volunteer:"):
        account_id = account.partition(":")[2]
        if account_id.isdigit():
            completed = completed.filter(assigned_volunteer_id=int(account_id))
        else:
            account = ""
    else:
        account = ""

    volunteer_ids = HelpRequest.objects.filter(
        status=HelpRequest.Status.COMPLETED, assigned_volunteer__isnull=False
    ).values_list("assigned_volunteer_id", flat=True).distinct()
    
    UserModel = get_user_model()
    volunteer_accounts = UserModel.objects.filter(pk__in=volunteer_ids).order_by("first_name", "last_name", "username")

    return render(request, "barangay/ratings.html", {
        "requests": completed.order_by("-updated_at"),
        "volunteer_accounts": volunteer_accounts,
        "active_account": account,
    })


@login_required
def barangay_pending_accounts(request):
    """List family member and volunteer accounts awaiting approval."""
    if not (request.user.is_superuser or request.user.role in ["staff", "admin"]):
        messages.error(request, "You do not have permission to approve accounts.")
        return redirect("dashboard_redirect")

    UserModel = get_user_model()
    pending_users = UserModel.objects.filter(
        is_approved=False,
        is_rejected=False,
        role__in=["requester", "volunteer"],
    ).order_by("date_joined")
    return render(request, "barangay/approvals.html", {"pending_users": pending_users})


@login_required
def barangay_approve_account(request, pk):
    """Approve a pending family member or volunteer account."""
    if not (request.user.is_superuser or request.user.role in ["staff", "admin"]):
        messages.error(request, "You do not have permission to approve accounts.")
        return redirect("dashboard_redirect")

    UserModel = get_user_model()
    pending_user = get_object_or_404(
        UserModel,
        pk=pk,
        is_approved=False,
        is_rejected=False,
        role__in=["requester", "volunteer"],
    )
    if request.method == "POST":
        pending_user.is_approved = True
        pending_user.save(update_fields=["is_approved"])
        messages.success(request, f"{pending_user.get_full_name() or pending_user.username} has been approved.")
    return redirect("barangay_pending_accounts")


@login_required
def barangay_reject_account(request, pk):
    """Mark a pending family member or volunteer account as rejected."""
    if not (request.user.is_superuser or request.user.role in ["staff", "admin"]):
        messages.error(request, "You do not have permission to reject accounts.")
        return redirect("dashboard_redirect")

    UserModel = get_user_model()
    pending_user = get_object_or_404(
        UserModel,
        pk=pk,
        is_approved=False,
        is_rejected=False,
        role__in=["requester", "volunteer"],
    )
    if request.method == "POST":
        account_name = pending_user.get_full_name() or pending_user.username
        pending_user.is_rejected = True
        pending_user.save(update_fields=["is_rejected"])
        messages.success(request, f"{account_name}'s account has been rejected. The account record was kept.")
    return redirect("barangay_pending_accounts")


@login_required
def barangay_request_detail(request, pk):
    """View details of a single request and update its status."""
    help_request = get_object_or_404(HelpRequest, pk=pk)

    if request.method == "POST":
        form = BarangayStatusForm(request.POST, instance=help_request)
        if form.is_valid():
            if form.cleaned_data["status"] != HelpRequest.Status.REJECTED:
                form.instance.rejection_reason = ""
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


# ==========================================
# Volunteer Views
# ==========================================

@login_required
def volunteer_list(request):
    """Displays open help requests available for volunteers to assist with."""
    requests = HelpRequest.objects.filter(
        status__in=[HelpRequest.Status.PENDING, HelpRequest.Status.IN_PROGRESS]
    )

    req_type = request.GET.get('request_type')
    barangay = request.GET.get('barangay')
    status_filter = request.GET.get('status')

    if req_type:
        requests = requests.filter(request_type=req_type)
    if barangay:
        requests = requests.filter(barangay__iexact=barangay)
    if status_filter:
        requests = requests.filter(status=status_filter)

    requests = requests.order_by('-created_at')

    available_barangays = (
        HelpRequest.objects.exclude(barangay__isnull=True)
        .exclude(barangay='')
        .values_list('barangay', flat=True)
        .distinct()
        .order_by('barangay')
    )

    context = {
        'requests': requests,
        'available_barangays': available_barangays,
        'request_types': HelpRequest.RequestType.choices,
        'status_choices': HelpRequest.Status.choices,
        'active_type': req_type,
        'active_barangay': barangay,
        'active_status': status_filter,
    }
    return render(request, 'volunteer/request_list.html', context)


@login_required
def volunteer_history(request):
    """Show a volunteer's completed or rejected assignments without family feedback."""
    requests = HelpRequest.objects.filter(
        assigned_volunteer=request.user,
        status__in=[HelpRequest.Status.COMPLETED, HelpRequest.Status.REJECTED],
    ).select_related("requester").order_by("-updated_at")
    return render(request, "volunteer/request_history.html", {"requests": requests})


@login_required
def volunteer_detail(request, pk):
    """Displays request details for volunteers."""
    help_request = get_object_or_404(HelpRequest, pk=pk)
    return render(
        request,
        "volunteer/request_detail.html",
        {"object": help_request},
    )


@login_required
def volunteer_claim_request(request, pk):
    help_request = get_object_or_404(
        HelpRequest, pk=pk, status=HelpRequest.Status.PENDING
    )
    if request.method == 'POST':
        help_request.status = HelpRequest.Status.IN_PROGRESS
        help_request.assigned_volunteer = request.user
        help_request.save()
        messages.success(request, f'You have claimed the request for {help_request.senior_name}.')
    return redirect('volunteer_detail', pk=help_request.pk)


@login_required
def volunteer_unclaim_request(request, pk):
    help_request = get_object_or_404(
        HelpRequest,
        pk=pk,
        status=HelpRequest.Status.IN_PROGRESS,
        assigned_volunteer=request.user
    )
    if request.method == 'POST':
        help_request.status = HelpRequest.Status.PENDING
        help_request.assigned_volunteer = None
        help_request.save()
        messages.info(request, 'You have released the request back to the pending queue.')
    return redirect('volunteer_list')


# ==========================================
# Admin Views
# ==========================================

@login_required
def admin_panel(request):
    if request.user.role != User.Role.ADMIN and not request.user.is_superuser:
        return HttpResponseForbidden("You are not authorized to view this page.")

    return render(request, 'admin/admin_panel.html')


@login_required
def admin_user_list(request, role):
    if request.user.role != User.Role.ADMIN and not request.user.is_superuser:
        return HttpResponseForbidden("You are not authorized to view this page.")

    role_titles = {
        'staff': 'Barangay Staff Accounts',
        'volunteer': 'Volunteer Accounts',
        'requester': 'Family Member Accounts',
    }

    users = User.objects.filter(role=role)
    title = role_titles.get(role, 'User Accounts')

    context = {
        'users': users,
        'role': role,
        'page_title': title,
    }
    return render(request, 'admin_panel/admin_user_list.html', context)