from django.contrib.auth import get_user_model
from django.views.generic import DetailView, RedirectView, UpdateView
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from .models import Client
from django.contrib.auth.mixins import LoginRequiredMixin


class ClientAddView(CreateView):
    model = Client
    fields = ["client_name", "email", "industry", "city"]
    success_url = reverse_lazy("admin:clients_client_changelist")


client_add_view = ClientAddView.as_view()


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    # slug_field = "username"
    # slug_url_kwarg = "username"
    fields = ["client_name", "email", "industry", "city"]


client_detail_view = ClientDetailView.as_view()


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    model = Client
    # fields = ["name"]
    fields = ["client_name", "email", "industry", "city"]
    # def get_success_url(self):
    #     return reverse("client:detail", kwargs={"username": self.request.user.username})

    # def get_object(self):
    #     return User.objects.get(username=self.request.user.username)


client_update_view = ClientUpdateView.as_view()


class ClientRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    # def get_redirect_url(self):
    #     return reverse("client:detail", kwargs={"username": self.request.user.username})


client_redirect_view = ClientRedirectView.as_view()
