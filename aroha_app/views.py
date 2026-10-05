from django.contrib import messages
from django.shortcuts import redirect, render
 
from .forms import SignUpForm
 
 
def signup(request):
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            "Account created! Please wait for an admin to approve it, then you can log in.",
        )
        return redirect("login")
    return render(request, "registration/signup.html", {"form": form})
 