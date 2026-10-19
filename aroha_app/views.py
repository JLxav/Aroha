from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import HelpRequestForm, SignUpForm, VolunteerFeedbackForm
from .models import HelpRequest


def homepage(request):
    """Render the public Aroha landing page."""
    return render(request, "landing.html")


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
    """Handles editing an existing pending request."""
    help_request = get_object_or_404(HelpRequest, pk=pk, requester=request.user)

    # Completed and rejected requests are read-only.
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
    """Allow a family member to delete their own pending request."""
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
    """Displays filterable and sortable help requests for barangay staff."""
    requests = HelpRequest.objects.all()

    # 1. Capture filter parameters from URL
    req_type = request.GET.get("request_type")
    barangay = request.GET.get("barangay")
    sort_order = request.GET.get("sort", "latest")

    # 2. Apply stacked filters
    if req_type:
        requests = requests.filter(request_type=req_type)
    if barangay:
        requests = requests.filter(barangay__iexact=barangay)

    # 3. Apply sorting
    if sort_order == "earliest":
        requests = requests.order_by("created_at")
    else:
        requests = requests.order_by("-created_at")

    # 4. Get unique barangays for the dropdown menu dynamically
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
        "request_types": HelpRequest.RequestType.choices,  # Assuming choices exist on your model
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
    User = get_user_model()
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
    volunteer_accounts = User.objects.filter(pk__in=volunteer_ids).order_by("first_name", "last_name", "username")

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
    User = get_user_model()
    pending_users = User.objects.filter(
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
    User = get_user_model()
    pending_user = get_object_or_404(
        User,
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
    User = get_user_model()
    pending_user = get_object_or_404(
        User,
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
  # Get requests that need volunteer assistance
  requests = HelpRequest.objects.filter(
      status__in=[HelpRequest.Status.PENDING, HelpRequest.Status.IN_PROGRESS]
  )

  # 1. Capture filter parameters from URL query string
  req_type = request.GET.get('request_type')
  barangay = request.GET.get('barangay')
  status_filter = request.GET.get('status')

  # 2. Apply stacked filters
  if req_type:
    requests = requests.filter(request_type=req_type)
  if barangay:
    requests = requests.filter(barangay__iexact=barangay)
  if status_filter:
    requests = requests.filter(status=status_filter)

  requests = requests.order_by('-created_at')

  # 3. Get unique barangays for filter dropdown
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
    """Displays request details. Volunteers can only view, not freely update status."""
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
        help_request.assigned_volunteer = request.user # <--- ADD THIS LINE
        help_request.save()
        messages.success(request, f'You have claimed the request for {help_request.senior_name}.')
    return redirect('volunteer_detail', pk=help_request.pk)

@login_required
def volunteer_unclaim_request(request, pk):
    help_request = get_object_or_404(
        HelpRequest, 
        pk=pk, 
        status=HelpRequest.Status.IN_PROGRESS,
        assigned_volunteer=request.user # Ensures only the volunteer who took it can drop it
    )
    if request.method == 'POST':
        help_request.status = HelpRequest.Status.PENDING
        help_request.assigned_volunteer = None
        help_request.save()
        messages.info(request, 'You have released the request back to the pending queue.')
    return redirect('volunteer_list')
