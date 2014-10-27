from django.conf.urls import url
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST, require_GET

from communication.models import Discussion
from content.admin import (TestingQuestionAdmin, TestingQuestion,
                           TestingQuestionOption)
from auth.admin import LearnerResource, LearnerAdmin, Learner
from oneplus.utils import update_metric
from import_export import fields
from django.db.models import Q
from organisation.models import School


def ensure_preview_session_state(view=None):
    '''
    View decorator that populates the session dict with
    the state required for a preview.
    '''
    def decorator(view_function):
        def new_function(request, object_id, *args, **kwargs):
            if "state" not in request.session:
                request.session["state"] = {}
            request.session.update({
                "next_tasks_today": 1,
                "discussion_page_max": Discussion.objects.filter(
                    question_id=object_id,
                    moderated=True,
                    response=None
                ).count(),
                "discussion_comment": False,
                "discussion_responded_id": None
            })
            request.session["state"]["discussion_page"] = \
                    min(2, request.session["state"]["discussion_page_max"])
            messages = Discussion.objects.filter(
                question_id=object_id,
                moderated=True,
                response=None
            ).order_by("publishdate") \
             .reverse()[:request.session["state"]["discussion_page"]]
            return view_function(request, object_id, *args,
                                 messages=messages, **kwargs)
        return new_function

    if view:
        return decorator(view)
    return decorator


def ensure_preview_session_state_empty(view=None):
    '''
    View decorator that populates the session dict with
    the empty state required for a preview.
    '''
    def decorator(view_function):
        def new_function(request, *args, **kwargs):
            if "state" not in request.session:
                request.session["state"] = {}
            request.session.update({
                "next_tasks_today": 1,
                "discussion_page_max": 0,
                "discussion_comment": False,
                "discussion_responded_id": None,
                "discussion_page": 0
            })
            return view_function(request, *args, messages=[], **kwargs)
        return new_function

    if view:
        return decorator(view)
    return decorator


class OnePlusLearnerResource(LearnerResource):
    class_name = fields.Field(column_name=u'class')
    completed_questions = fields.Field(column_name=u'completed_questions')
    percentage_correct = fields.Field(column_name=u'percentage_correct')

    class Meta:
        model = Learner
        exclude = (
            'customuser_ptr', 'password', 'last_login', 'is_superuser',
            'groups', 'user_permissions', 'is_staff', 'is_active',
            'date_joined', 'unique_token', 'unique_token_expiry'
            'welcome_message_sent', 'welcome_message'
        )
        export_order = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'mobile',
            'school',
            'country',
            'area',
            'city',
            'optin_sms',
            'optin_email',
            'completed_questions',
            'percentage_correct',
            'class_name',
        )

    def import_obj(self, obj, data, dry_run):
        school, created = School.objects.get_or_create(name=data[u'school'])
        data[u'school'] = school.id
        data[u'mobile'] = data[u'username']
        return super(LearnerResource, self)\
            .import_obj(obj, data, dry_run)

    def import_data(self, dataset, **kwargs):

        if not kwargs["dry_run"]:
            count = dataset.height
            update_metric(
                "running.registered.participants",
                int(count),
                "SUM",
            )

        return super(LearnerResource, self).import_data(dataset, **kwargs)


class OnePlusLearnerAdmin(LearnerAdmin):
    resource_class = OnePlusLearnerResource

    def save_model(self, request, obj, form, change):
        before_total = Learner.objects.all().count()
        super(type(self), self).save_model(request, obj, form, change)
        total = Learner.objects.all().count()
        update_metric(
            "registered.participants",
            total,
            'LAST'
        )

        if total > 0:
            opt_ins = float(Learner.objects.filter(
                Q(optin_sms=True) | Q(optin_email=True)).count()) / float(total)

            update_metric(
                "percentage.optin",
                opt_ins * 100,
                'LAST'
            )

        if total != before_total:
            update_metric(
                "running.registered.participants",
                total - before_total,
                "SUM",
            )


class TestingQuestionLinkAdmin(TestingQuestionAdmin):
    list_display = TestingQuestionAdmin.list_display + ("preview_link",)

    def preview_link(self, obj):
        return u'<a href="%s">Preview</a>' % reverse(
            'admin:question_preview',
            kwargs={'object_id': obj.id}
        )
    preview_link.allow_tags = True
    preview_link.short_description = "Preview"

    def get_urls(self):
        urls = super(TestingQuestionLinkAdmin, self).get_urls()
        return [
            url(r'^(?P<object_id>\d+)/preview/$',
                self.admin_site.admin_view(self.preview_view),
                name='question_preview'),
            url(r'^(?P<object_id>\d+)/preview/(?P<result>right|wrong)/$',
                self.admin_site.admin_view(self.preview_result_view),
                name='question_preview_result'),
            url(r'^add/preview/$',
                self.admin_site.admin_view(self.preview_add_view),
                name='question_preview_add'),
            url(r'^(?P<object_id>\d+)/preview/unsaved/$',
                self.admin_site.admin_view(self.preview_change_view),
                name='question_preview_change'),
        ] + urls

    def add_view(self, request, form_url='', extra_context=None):
        request.session.pop("admin_question_data", None)
        return super(TestingQuestionLinkAdmin, self).add_view(
            request,
            form_url=form_url or reverse('admin:question_preview_add'),
            extra_context=extra_context
        )

    def change_view(self, request, object_id, form_url='', extra_context=None):
        request.session.pop("admin_question_data", None)
        return super(TestingQuestionLinkAdmin, self).change_view(
            request,
            object_id,
            form_url=form_url or reverse('admin:question_preview_change',
                                         kwargs={'object_id': object_id}),
            extra_context=extra_context
        )

    @method_decorator(ensure_preview_session_state_empty)
    def preview_add_view(self, request, **kwargs):
        if request.method == "GET" or len(request.POST) == 1 or \
                "answer" in request.POST:
            if "admin_question_data" not in request.session:
                return HttpResponseRedirect(
                    reverse("admin:content_testingquestion_add")
                )
            form_data = request.session["admin_question_data"]
        else:
            form_data = request.POST
            request.session["admin_question_data"] = form_data

        form = self.get_form(request)(form_data)
        inline_formset = [f for f in self.get_formsets(request)][0]
        inline_formset = inline_formset(form_data)

        if form.is_valid() and inline_formset.is_valid():
            # use the form data to render the preview page
            # instead of the saved object
            question = form.save(commit=False)
            inline_objects = inline_formset.save(commit=False)
            return render(request, "admin/preview_next.html", {
                "question": question,
                "options": inline_objects,
                "show_correct": True,
                "messages": kwargs['messages'],
                "form_url": reverse("admin:question_preview_add"),
                "save_form": form,
                "save_formset": inline_formset,
                "save_form_url": reverse("admin:content_testingquestion_add")
            })

        return self.add_view(request)

    @method_decorator(ensure_preview_session_state)
    def preview_change_view(self, request, object_id, **kwargs):
        if request.method == "GET" or len(request.POST) == 1 or \
                "answer" in request.POST:
            if "admin_question_data" not in request.session:
                return HttpResponseRedirect(
                    reverse("admin:content_testingquestion_change",
                            args=(object_id, ))
                )
            form_data = request.session["admin_question_data"]
        else:
            form_data = request.POST
            request.session["admin_question_data"] = form_data

        instance = TestingQuestion.objects.get(id=object_id)
        form = self.get_form(request)(form_data, instance=instance)
        inline_formset = [f for f in self.get_formsets(request, instance)][0]
        inline_formset = inline_formset(form_data, instance=instance)

        if form.is_valid() and inline_formset.is_valid():
            # use the form data to render the preview page
            # instead of the saved object
            question = form.save(commit=False)
            inline_formset.save(commit=False)
            inline_objects = list(instance.testingquestionoption_set.exclude(
                id__in=[o.pk for o in (inline_formset.changed_objects +
                                       inline_formset.deleted_objects)]
            )) + inline_formset.new_objects
            return render(request, "admin/preview_next.html", {
                "question": question,
                "options": inline_objects,
                "show_correct": True,
                "messages": kwargs['messages'],
                "form_url": reverse("admin:question_preview_change",
                                    kwargs={'object_id': object_id}),
                "save_form": form,
                "save_formset": inline_formset,
                "save_form_url": reverse("admin:content_testingquestion_change",
                                         args=(object_id, ))
            })

        return self.change_view(request, object_id)

    @method_decorator(ensure_preview_session_state)
    def preview_view(self, request, object_id, **kwargs):
        question = get_object_or_404(TestingQuestion, id=object_id)

        # answer provided
        if request.method == 'POST' and 'answer' in request.POST:
            ans_id = request.POST["answer"]
            option = get_object_or_404(TestingQuestionOption,
                                       question_id=object_id,
                                       id=ans_id)
            return HttpResponseRedirect(reverse(
                'admin:question_preview_result',
                kwargs={
                    'object_id': object_id,
                    'result': ('right' if option.correct else 'wrong')
                }
            ))

        return render(request, "learn/next.html", {
            "question": question,
            "messages": kwargs['messages'],
            "form_url": reverse("admin:question_preview",
                                kwargs={'object_id': object_id}),
        })

    @method_decorator(require_GET)
    @method_decorator(ensure_preview_session_state)
    def preview_result_view(self, request, object_id, result, **kwargs):
        question = get_object_or_404(TestingQuestion, id=object_id)

        return render(request, "learn/%s.html" % result, {
            "question": question,
            "messages": kwargs['messages'],
            "home_url": reverse("admin:content_testingquestion_changelist"),
            "points": 1
        })


admin.site.unregister(TestingQuestion)
admin.site.unregister(Learner)
admin.site.register(TestingQuestion, TestingQuestionLinkAdmin)
admin.site.register(Learner, OnePlusLearnerAdmin)
