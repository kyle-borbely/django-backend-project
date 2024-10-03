from django.urls import reverse_lazy
from django.views.generic import DetailView, RedirectView, UpdateView
from django.views.generic.edit import CreateView
from .models import Coach


class CoachAddView(CreateView):
    model = Coach
    fields = [
        "first_name",
        "last_name",
        "email",
    ]
    success_url = reverse_lazy("coach_detail")


coache_add_view = CoachAddView.as_view()


class CoachDetailView(DetailView):
    model = Coach
    template_name = "coach_detail.html"


coach_detail_view = CoachDetailView.as_view()


class CoachUpdateView(UpdateView):
    model = Coach
    template_name = "coach_update.html"
    fields = [
        "first_name",
        "last_name",
        "email",
    ]


coach_update_view = CoachUpdateView.as_view()
