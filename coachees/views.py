from django.views import View
from coaches.models import Coach
from coachees.models import EngagementInfo, Coachee
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from .models import (
    Session,
    CoacheesReviews,
    CoachReviews,
    CoachFinalReportReview,
    CoacheesFinalReportReview,
)
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin
from calm_darkness_38642.schedular import notifications


class AssignCoachView(LoginRequiredMixin, View):
    template_name = "assign_coach.html"

    def get(self, request, pk):
        coachee = Coachee.objects.get(pk=pk)
        coaches = Coach.objects.all().order_by("first_name")

        # Get the already assigned coach and number of sessions for the coachee
        engagement_infos = coachee.engagement_infos.all()
        selected_coach_ids = [info.coach.id for info in engagement_infos]
        num_sessions = coachee.num_sessions
        choices = [("all", "All")] + [(str(coach), str(coach)) for coach in coaches]

        selected_filter = request.GET.get("coach_filter", "all")
        if selected_filter == "all":
            filtered_coaches = coaches
        else:
            filtered_coaches = coaches.filter(name=selected_filter)

        already_assigned_coaches = coachee.engagement_infos.values_list(
            "coach", flat=True
        )
        assigned_coaches = Coach.objects.filter(pk__in=already_assigned_coaches)

        return render(
            request,
            self.template_name,
            {
                "coachee": coachee,
                "coaches": filtered_coaches,
                "assigned_coaches": assigned_coaches,
                "coach_filter_choices": choices,
                "selected_coach_filter": selected_filter,
                "selected_coach_ids": selected_coach_ids,
                "num_sessions": num_sessions,
            },
        )

    @transaction.atomic
    def post(self, request, pk):
        coachee = Coachee.objects.get(pk=pk)
        selected_coach_ids = request.POST.getlist("coach_id")
        # get the list of selected coach IDs
        num_sessions = request.POST.get("num-sessions")

        # Check to not change anything after Start Engagement with any coach.
        if coachee.engagement_status == "Start Engagement":
            # Get the already assigned coach and number of sessions for the coachee
            coaches = Coach.objects.all()
            engagement_infos = coachee.engagement_infos.all()
            selected_coach_ids = [info.coach.id for info in engagement_infos]
            num_sessions = coachee.num_sessions
            choices = [("all", "All")] + [(str(coach), str(coach)) for coach in coaches]

            selected_filter = request.GET.get("coach_filter", "all")
            if selected_filter == "all":
                filtered_coaches = coaches
            else:
                filtered_coaches = coaches.filter(name=selected_filter)

            already_assigned_coaches = coachee.engagement_infos.values_list(
                "coach", flat=True
            )
            assigned_coaches = Coach.objects.filter(pk__in=already_assigned_coaches)
            context = {
                "coachee": coachee,
                "coaches": filtered_coaches,
                "assigned_coaches": assigned_coaches,
                "coach_filter_choices": choices,
                "selected_coach_filter": selected_filter,
                "selected_coach_ids": selected_coach_ids,
                "num_sessions": num_sessions,
                "error_message": "You couldn't change coaches or number of sessions after engagement started with any coach.",
            }
            return render(request, self.template_name, context)

        # Get the coaches that are already assigned to the coachee
        already_assigned_coaches = coachee.engagement_infos.values_list(
            "coach", flat=True
        )

        # Determine the coaches to be deselected (already assigned but not selected in the form)
        deselected_coaches = Coach.objects.filter(
            pk__in=already_assigned_coaches
        ).exclude(pk__in=selected_coach_ids)

        if deselected_coaches:
            # Delete the deselected coaches from the engagement_infos table
            coachee.engagement_infos.filter(coach__in=deselected_coaches).delete()

        if selected_coach_ids:
            selected_coaches = Coach.objects.filter(pk__in=selected_coach_ids)
            # get the list of selected coaches

            # Get the coaches that are not already assigned to the coachee
            unassigned_coaches = selected_coaches.exclude(
                pk__in=already_assigned_coaches
            )

            with transaction.atomic():
                for coach in unassigned_coaches:
                    engagement_info = EngagementInfo(coachee=coachee, coach=coach)
                    engagement_info.save()
                coachee.num_sessions = num_sessions
                coachee.coaching_status = "Assigned"
                coachee.save()
                # sending notification to the coachee
                notifications(
                    action_type="assign_coaches",
                    user_id=coachee.user_id,
                    notification_name="You have been assigned Coaches! Please take a look at their profiles and schedule Chemistry Calls.",
                    notification_text="",
                    fcm_data={"action_type": "assign_coaches"},
                )
            messages.success(request, "Coaches successfully assigned to coachee.")
            changelist_url = reverse("admin:coachees_coachee_changelist")
            return redirect(changelist_url)
        else:
            context = {
                "coachee": coachee,
                "assigned_coaches": Coach.objects.filter(pk__in=selected_coach_ids),
                "coaches": Coach.objects.all(),
                "num_sessions": num_sessions,
                "error_message": "Please select one or more coaches and enter the number of sessions.",
            }
            return render(request, self.template_name, context)


def session_report(request, session_id):
    try:
        session_obj = Session.objects.get(id=session_id)
        coachee_object = Coachee.objects.get(id=session_obj.engagement_info.coachee_id)
        coach_obj = Coach.objects.get(id=session_obj.engagement_info.coach_id)
        coach_review = CoachReviews.objects.filter(session_id=session_obj.id)
        coachee_review = CoacheesReviews.objects.filter(session_id=session_obj.id)
        return render(
            request,
            "admin/coachees/coaching_report.html",
            {
                "coachee": coachee_object,
                "session": session_obj,
                "coach": coach_obj,
                "coach_review": coach_review.first(),
                "coachee_review": coachee_review.first(),
            },
        )
    except:
        return HttpResponseRedirect("/admin/coachees/coachee/")


def final_report(request, engagement_id):
    try:
        engagement_info = EngagementInfo.objects.get(id=engagement_id)
        coachee_object = Coachee.objects.get(id=engagement_info.coachee_id)
        coach_obj = Coach.objects.get(id=engagement_info.coach_id)
        coach_review = CoachFinalReportReview.objects.filter(
            engagement_info_id=engagement_id
        )
        coachee_review = CoacheesFinalReportReview.objects.filter(
            engagement_info_id=engagement_id
        )
        return render(
            request,
            "admin/coachees/final_report.html",
            {
                "coach": coach_obj,
                "coachee": coachee_object,
                "engagement": engagement_info,
                "coach_review": coach_review.first() if coach_review.exists() else None,
                "coachee_review": coachee_review.first()
                if coachee_review.exists()
                else None,
            },
        )
    except:
        return HttpResponseRedirect("/admin/coachees/coachee/")
