from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from django.utils.translation import ugettext
from django.views.generic import ListView

from data_sources.models import DataSource
from users.forms import UserProfileUpdateForm


@login_required
def dashboard_home(request):
    logout_next = reverse('login')
    return render(request, 'dashboard/welcome_page.html', {
        'logout_next': logout_next,
    })


@login_required
def dashboard_profile_update(request):
    logout_next = reverse('index')
    if request.method == 'POST':
        form = UserProfileUpdateForm(
            data=request.POST, files=request.FILES,
            instance=request.user,
        )
        if form.is_valid():
            form.save()
            messages.success(request, ugettext(
                'Your profile has been updated successfully.',
            ))
            return redirect('dashboard_home')
    else:
        form = UserProfileUpdateForm(instance=request.user)
    return render(request, 'dashboard/profile.html', {
        'form': form, 'logout_next': logout_next,
    })


class UserDataSourceListView(LoginRequiredMixin, ListView):

    model = DataSource

    template_name = 'dashboard/data_source_validation.html'

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


