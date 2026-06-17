from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import RegisterForm, SubscriptionForm
from .models import TelegramProfile


def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("catalog:movie_list")
    return render(request, "registration/register.html", {"form": form})


@login_required
def subscriptions(request):
    initial = {}
    if request.GET.get("movie"):
        initial["movie"] = request.GET["movie"]
    form = SubscriptionForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        sub = form.save(commit=False)
        sub.user = request.user
        sub.save()
        return redirect("accounts:subscriptions")

    profile, _ = TelegramProfile.objects.get_or_create(user=request.user)
    bot = settings.TELEGRAM_BOT_USERNAME
    telegram_link = f"https://t.me/{bot}?start={profile.link_code}" if bot else ""
    subs = request.user.subscriptions.select_related("movie", "cinema")
    return render(
        request,
        "accounts/subscriptions.html",
        {
            "form": form,
            "subscriptions": subs,
            "telegram_linked": bool(profile.chat_id),
            "telegram_link": telegram_link,
        },
    )


@login_required
def subscription_delete(request, pk):
    if request.method == "POST":
        request.user.subscriptions.filter(pk=pk).delete()
    return redirect("accounts:subscriptions")
