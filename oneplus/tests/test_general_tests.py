# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import logging
from auth.models import Learner, CustomUser
from communication.models import Post, PostComment, CoursePostRel
from content.models import TestingQuestion, TestingQuestionOption, Event, EventStartPage, EventEndPage, EventQuestionRel
from core.models import Class, Participant, ParticipantQuestionAnswer, Setting
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.test import TestCase, Client
from django.test.utils import override_settings
from gamification.models import GamificationBadgeTemplate, GamificationScenario
from go_http.tests.test_send import RecordingHandler
from mock import patch
from oneplus.auth_views import space_available
from oneplus.models import LearnerState
from oneplus.views import get_week_day
from organisation.models import Course, Module, CourseModuleRel, Organisation, School


def append_query_params(url, params):
    if len(params) < 1:
        return url
    return '%s?%s' % (url, '&'.join([('%s=%s' % (idx, params[idx])) for idx in params.keys()]))


def create_test_question(name, module, **kwargs):
        return TestingQuestion.objects.create(name=name, module=module, **kwargs)


def create_course(name="course name", **kwargs):
    return Course.objects.create(name=name, **kwargs)


def create_module(name, course, **kwargs):
    module = Module.objects.create(name=name, **kwargs)
    rel = CourseModuleRel.objects.create(course=course, module=module)
    module.save()
    rel.save()
    return module


def create_class(name, course, **kwargs):
    return Class.objects.create(name=name, course=course, **kwargs)


def create_organisation(name='organisation name', **kwargs):
    return Organisation.objects.create(name=name, **kwargs)


def create_school(name, organisation, **kwargs):
    return School.objects.create(
        name=name, organisation=organisation, **kwargs)


def create_learner(school, **kwargs):
    if 'grade' not in kwargs:
        kwargs['grade'] = 'Grade 11'
    if 'terms_accept' not in kwargs:
        kwargs['terms_accept'] = True
    return Learner.objects.create(school=school, **kwargs)


def create_participant(learner, classs, **kwargs):
    participant = Participant.objects.create(
        learner=learner, classs=classs, **kwargs)
    return participant


def create_badgetemplate(name='badge template name', **kwargs):
    return GamificationBadgeTemplate.objects.create(
        name=name,
        image="none",
        **kwargs)


def create_test_question_option(name, question, correct=True):
    return TestingQuestionOption.objects.create(
        name=name, question=question, correct=correct)


def create_test_answer(
        participant,
        question,
        option_selected,
        answerdate):
    return ParticipantQuestionAnswer.objects.create(
        participant=participant,
        question=question,
        option_selected=option_selected,
        answerdate=answerdate,
        correct=False
    )


def create_and_answer_questions(num_questions, module, participant, prefix, date):
    answers = []
    for x in range(0, num_questions):
        # Create a question
        question = create_test_question(
            'q' + prefix + str(x), module)

        question.save()
        option = create_test_question_option(
            'option_' + prefix + str(x),
            question)
        option.save()
        answer = create_test_answer(
            participant=participant,
            question=question,
            option_selected=option,
            answerdate=date
        )
        answer.save()
        answers.append(answer)

    return answers


def create_event(name, course, activation_date, deactivation_date, **kwargs):
    return Event.objects.create(name=name, course=course, activation_date=activation_date,
                                deactivation_date=deactivation_date, **kwargs)


def create_event_start_page(event, header, paragraph):
    return EventStartPage.objects.create(event=event, header=header, paragraph=paragraph)


def create_event_end_page(event, header, paragraph):
    return EventEndPage.objects.create(event=event, header=header, paragraph=paragraph)


def create_event_question(event, question, order):
    return EventQuestionRel.objects.create(event=event, question=question, order=order)


@override_settings(JUNEBUG_FAKE=True)
class GeneralTests(TestCase):

    def setUp(self):

        self.course = create_course()
        self.classs = create_class('class name', self.course)
        self.organisation = create_organisation()
        self.school = create_school('school name', self.organisation)
        self.learner = create_learner(
            self.school,
            username="+27123456789",
            mobile="+27123456789",
            country="country",
            area="Test_Area",
            unique_token='abc123',
            unique_token_expiry=datetime.now() + timedelta(days=30),
            is_staff=True)
        self.participant = create_participant(
            self.learner, self.classs, datejoined=datetime(2014, 7, 18, 1, 1))
        self.module = create_module('module name', self.course)
        self.badge_template = create_badgetemplate()

        self.scenario = GamificationScenario.objects.create(
            name='scenario name',
            event='1_CORRECT',
            course=self.course,
            module=self.module,
            badge=self.badge_template
        )

        self.outgoing_vumi_text = []
        self.outgoing_vumi_metrics = []
        self.handler = RecordingHandler()
        logger = logging.getLogger('DEBUG')
        logger.setLevel(logging.INFO)
        logger.addHandler(self.handler)

        self.admin_user_password = 'mypassword'
        self.admin_user = CustomUser.objects.create_superuser(
            username='asdf33',
            email='asdf33@example.com',
            password=self.admin_user_password,
            mobile='+27111111133')

    def test_get_next_question(self):
        create_test_question('question1', self.module, state=3)
        learnerstate = LearnerState.objects.create(
            participant=self.participant,
            active_question=None
        )

        # get next question
        learnerstate.getnextquestion()
        learnerstate.save()

        # check active question
        self.assertEquals(learnerstate.active_question.name, 'question1')

    def test_home(self):
            self.client.get(reverse(
                'auth.autologin',
                kwargs={'token': self.learner.unique_token})
            )

            #no questions
            resp = self.client.get(reverse('learn.home'))
            self.assertEquals(resp.status_code, 200)

            #with questions
            create_test_question('question1', self.module, state=3)
            LearnerState.objects.create(
                participant=self.participant,
                active_question=None,
            )
            resp = self.client.get(reverse('learn.home'))
            self.assertEquals(resp.status_code, 200)

            #post with no event
            resp = self.client.post(reverse('learn.home'), data={"take_event": "event"}, follow=True)
            self.assertEquals(resp.status_code, 200)

            #with event active
            event_module = create_module("event_module", self.course, type=2)
            event = create_event("event_name", self.course, datetime.now() - timedelta(days=1),
                                 datetime.now() + timedelta(days=1), number_sittings=2, event_points=5, type=1)
            start_page = create_event_start_page(event, "Test Start Page", "Test Start Page Paragraph")
            end_page = create_event_end_page(event, "Test End Page", "Test Start Page Paragraph")
            question_1 = create_test_question("question_1", event_module, state=3)
            question_option_1 = create_test_question_option("question_1_option", question_1)
            create_event_question(event, question_1, 1)
            question_2 = create_test_question("question_2", event_module, state=3)
            question_option_2 = create_test_question_option("question_2_option", question_2)
            create_event_question(event, question_2, 2)

            resp = self.client.get(reverse('learn.home'))
            self.assertEquals(resp.status_code, 200)
            self.assertContains(resp, "Take the %s" % event.name)

            #no data in post
            resp = self.client.post(reverse('learn.home'), follow=True)
            self.assertEquals(resp.status_code, 200)

            #take event
            resp = self.client.post(reverse('learn.home'), data={"take_event": "event"}, follow=True)
            self.assertRedirects(resp, "event_start_page")
            self.assertContains(resp, start_page.header)

            #go to event_start_page
            resp = self.client.post(reverse("learn.event_start_page"),
                                    data={"event_start_button": "Get Started"}, follow=True)
            self.assertRedirects(resp, "event")

            #valid correct answer
            resp = self.client.post(reverse('learn.event'),
                                    data={'answer': question_option_1.id},
                                    follow=True)
            self.assertEquals(resp.status_code, 200)
            self.assertRedirects(resp, "event_right")

            resp = self.client.get(reverse('learn.home'))
            self.assertEquals(resp.status_code, 200)
            self.assertContains(resp, "Finish %s" % event.name)

            #take event the second time
            resp = self.client.post(reverse('learn.home'), data={"take_event": "event"}, follow=True)
            self.assertRedirects(resp, "event")

            #valid correct answer
            resp = self.client.post(reverse('learn.event'),
                                    data={'answer': question_option_2.id},
                                    follow=True)
            self.assertEquals(resp.status_code, 200)
            self.assertRedirects(resp, "event_right")

            resp = self.client.get(reverse('learn.event_end_page'))
            self.assertEquals(resp.status_code, 200)

            for i in range(1, 15):
                question = TestingQuestion.objects.create(name="Question %d" % i, module=self.module)
                option = TestingQuestionOption.objects.create(name="Option %d.1" % i, question=question, correct=True)
                ParticipantQuestionAnswer.objects.create(participant=self.participant, question=question,
                                                         option_selected=option, correct=True)

            question = TestingQuestion.objects.create(name="Question %d" % 15, module=self.module)
            option = TestingQuestionOption.objects.create(name="Option %d.1" % 15, question=question, correct=False)
            ParticipantQuestionAnswer.objects.create(participant=self.participant, question=question,
                                                     option_selected=option, correct=False)

            Setting.objects.create(key="REPEATING_QUESTIONS_ACTIVE", value="true")

            resp = self.client.get(reverse('learn.home'))
            self.assertEquals(resp.status_code, 200)
            self.assertContains(resp, "Redo incorrect answers")

    def test_first_time(self):
        self.client.get(reverse(
            'auth.autologin',
            kwargs={'token': self.learner.unique_token})
        )

        resp = self.client.get(reverse('learn.first_time'))
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(reverse('learn.first_time'), follow=True)
        self.assertEquals(resp.status_code, 200)

    def test_faq(self):
        self.client.get(reverse(
            'auth.autologin',
            kwargs={'token': self.learner.unique_token})
        )

        resp = self.client.get(reverse('misc.faq'))
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(reverse('misc.faq'), follow=True)
        self.assertEquals(resp.status_code, 200)

    def test_terms(self):
        self.client.get(reverse(
            'auth.autologin',
            kwargs={'token': self.learner.unique_token})
        )

        resp = self.client.get(reverse('misc.terms'))
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(reverse('misc.terms'), follow=True)
        self.assertEquals(resp.status_code, 200)

    def test_blog(self):
        self.client.get(
            reverse('auth.autologin',
                    kwargs={'token': self.learner.unique_token})
        )

        blog = Post.objects.create(
            name='testblog',
            publishdate=datetime.now()
        )
        CoursePostRel.objects.create(course=self.course, post=blog)

        resp = self.client.get(
            reverse('com.blog',
                    kwargs={'blogid': blog.id})
        )
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(
            reverse('com.blog',
                    kwargs={'blogid': blog.id})
        )
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(
            reverse('com.blog',
                    kwargs={'blogid': blog.id}),
            data={'comment': 'New comment'},
            follow=True
        )

        self.assertEquals(resp.status_code, 200)
        self.assertContains(resp, "Thank you for your contribution. Your message will display shortly!")

        pc = PostComment.objects.get(post=blog)
        self.assertEquals(pc.moderated, True)

        resp = self.client.post(
            reverse('com.blog',
                    kwargs={'blogid': blog.id}),
            data={'page': 1},
            follow=True
        )

        self.assertEquals(resp.status_code, 200)

    def test_welcome_screen(self):
        resp = self.client.get(reverse('misc.welcome'))
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(reverse('misc.welcome'), follow=True)
        self.assertEquals(resp.status_code, 200)

    def test_about_screen(self):
        resp = self.client.get(reverse('misc.about'))
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(reverse('misc.about'), follow=True)
        self.assertEquals(resp.status_code, 200)

    def test_contact_screen(self):
        resp = self.client.get(reverse('misc.contact'))
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(reverse('misc.contact'), follow=True)
        self.assertContains(resp, "Please complete the following fields:")

        resp = self.client.post(
            reverse("misc.contact"),
            follow=True,
            data={
                "fname": "Test",
                "sname": "test",
                "contact": "0123456789",
                "comment": "test",
                "school": "Test School",
                "grade": "11",
            }
        )

        self.assertContains(resp, "Your message has been sent. We will get back to you in the next 24 hours")

    def test_contact_screen_with_failure_and_bad_data(self):
        with patch("oneplus.misc_views.mail_managers") as mock_mail_managers:
            mock_mail_managers.side_effect = KeyError('e')

            resp = self.client.post(
                reverse("misc.contact"),
                follow=True,
                data={
                    "fname": "Test",
                    "sname": "test",
                    "contact": "0123456789\n0123456789\n0123456789",
                    "comment": "test",
                    "school": "Test School",
                    "grade": "11"
                }
            )

            self.assertContains(resp, "Your message has been sent. We will get back to you in the next 24 hours")
            mock_mail_managers.assert_called()

    def test_get_week_day(self):
        day = get_week_day()
        self.assertLess(day, 7)
        self.assertGreaterEqual(day, 0)

    def test_menu_screen(self):
        self.client.get(reverse(
            'auth.autologin',
            kwargs={'token': self.learner.unique_token})
        )

        #create event_session variable
        s = self.client.session
        s["event_session"] = True
        s.save()

        resp = self.client.get(reverse('core.menu'))
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(reverse('core.menu'), follow=True)
        self.assertEquals(resp.status_code, 200)

    def test_getconnected(self):
        resp = self.client.post(
            reverse('auth.getconnected')
        )
        self.assertContains(resp, "GET CONNECTED")

        learner = Learner.objects.create_user(
            username="+27891234567",
            mobile="+27891234567",
            password='1234'
        )

        create_participant(learner, self.classs, datejoined=datetime.now())
        self.client.post(
            reverse('auth.login'),
            data={
                'username': "+27891234567",
                'password': '1234'},
            follow=True
        )

        resp = self.client.post(
            reverse('auth.getconnected')
        )
        self.assertContains(resp, "GET CONNECTED")

    def test_points_screen(self):
        self.client.get(
            reverse('auth.autologin', kwargs={'token': self.learner.unique_token})
        )
        resp = self.client.get(reverse('prog.points'))
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(reverse('prog.points'), follow=True)
        self.assertEquals(resp.status_code, 200)

    def test_ontrack_screen(self):
        self.client.get(
            reverse('auth.autologin', kwargs={'token': self.learner.unique_token})
        )

        resp = self.client.get(reverse('prog.ontrack'))
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(reverse('prog.ontrack'), follow=True)
        self.assertEquals(resp.status_code, 200)

        #more than 10 answered
        create_and_answer_questions(11, self.module, self.participant, "name", datetime.now())
        resp = self.client.get(reverse('prog.ontrack'))
        self.assertEquals(resp.status_code, 200)

    def test_bloglist_screen(self):
        self.client.get(reverse('auth.autologin', kwargs={'token': self.learner.unique_token}))
        resp = self.client.get(reverse('com.bloglist'))
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(reverse('com.bloglist'), follow=True)
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(
            reverse('com.bloglist'),
            data={'page': 1},
            follow=True
        )

        self.assertEquals(resp.status_code, 200)

    def test_bloghero_screen(self):
        self.client.get(reverse('auth.autologin', kwargs={'token': self.learner.unique_token}))
        resp = self.client.get(reverse('com.bloghero'))
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(reverse('com.bloghero'), follow=True)
        self.assertEquals(resp.status_code, 200)

    def test_badge_screen(self):
        self.client.get(reverse('auth.autologin', kwargs={'token': self.learner.unique_token}))
        resp = self.client.get(reverse('prog.badges'))
        self.assertEquals(resp.status_code, 200)

        resp = self.client.post(reverse('prog.badges'), follow=True)
        self.assertEquals(resp.status_code, 200)

    def test_signout_screen(self):
        self.client.get(reverse('auth.autologin', kwargs={'token': self.learner.unique_token}))
        resp = self.client.get(reverse('auth.signout'))
        self.assertEquals(resp.status_code, 302)

        resp = self.client.post(reverse('auth.signout'), follow=True)
        self.assertEquals(resp.status_code, 200)

    def test_dashboard(self):
        c = Client()
        c.login(username=self.admin_user.username, password=self.admin_user_password)
        resp = c.get(reverse('dash.board'))
        self.assertContains(resp, 'sapphire')

    def test_dashboard_data(self):
        c = Client()
        c.login(username=self.admin_user.username, password=self.admin_user_password)
        resp = c.get(reverse('dash.data'))
        self.assertContains(resp, 'num_email_optin')

        resp = c.post(reverse('dash.data'))
        self.assertContains(resp, 'post office')

    def test_admin_auth_app_changes(self):
        c = Client()
        c.login(username=self.admin_user.username, password=self.admin_user_password)
        resp = c.get('/admin/auth/')
        self.assertContains(resp, 'User Permissions')

    def test_get_courses(self):
        c = Client()
        c.login(username=self.admin_user.username, password=self.admin_user_password)

        resp = c.get('/courses')
        self.assertContains(resp, '"name": "course name"')

    def test_get_classes(self):
        c = Client()
        c.login(username=self.admin_user.username, password=self.admin_user_password)

        create_class(name='test class 42', course=self.course)

        resp = c.get('/classes/all')
        self.assertContains(resp, '"name": "class name"')
        self.assertContains(resp, '"name": "test class 42"')

        resp = c.get('/classes/%s' % self.course.id)
        self.assertContains(resp, '"name": "class name"')

        resp = c.get('/classes/abc')
        self.assertEquals(resp.status_code, 200)

        resp = c.get('/classes/%s' % 999)
        self.assertEquals(resp.status_code, 200)

    def test_space_available(self):
        maximum = int(Setting.objects.get(key="MAX_NUMBER_OF_LEARNERS").value)
        total_reg = Participant.objects.aggregate(registered=Count('id'))
        available = maximum - total_reg.get('registered')

        learner = create_learner(
            self.school,
            username="+27123456999",
            mobile="+2712345699", )

        self.participant = create_participant(
            learner,
            self.classs,
            datejoined=datetime.now())
        available -= 1

        space, number_spaces = space_available()
        self.assertEquals(space, True)
        self.assertEquals(number_spaces, available)

        learner2 = self.learner = create_learner(
            self.school,
            username="+27123456988",
            mobile="+2712345688")

        self.participant = create_participant(
            learner2,
            self.classs,
            datejoined=datetime.now())
        available -= 1

        space, number_spaces = space_available()

        self.assertEquals(space, True)
        self.assertEquals(number_spaces, available)

    def test_participant_required_decorator(self):
        learner = create_learner(
            self.school,
            username="+27987654321",
            mobile="+27987654321",
            country="country",
            area="Test_Area",
            unique_token='cba321',
            unique_token_expiry=datetime.now() + timedelta(days=30),
            is_staff=True)
        participant = create_participant(
            learner, self.classs, datejoined=datetime(2014, 7, 18, 1, 1))
        self.client.get(reverse('auth.autologin',
                                kwargs={'token': learner.unique_token}))

        # participant exists
        resp = self.client.get(reverse('learn.home'), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "WELCOME")

        # participant doesn't exist
        participant.delete()
        resp = self.client.get(reverse('learn.home'), follow=True)
        self.assertRedirects(resp, reverse('auth.login'))

    def test_view_adminpreview(self):

        password = 'mypassword'
        my_admin = CustomUser.objects.create_superuser(
            username='asdf',
            email='asdf@example.com',
            password=password,
            mobile='+27111111111')
        c = Client()
        c.login(username=my_admin.username, password=password)

        self.question = create_test_question(
            'question1',
            self.module,
            question_content='test question')
        self.questionoption = create_test_question_option(
            'questionoption1',
            self.question)

        resp = c.get(
            reverse(
                'learn.preview',
                kwargs={
                    'questionid': self.question.id}))

        self.assertContains(resp, "test question")

        # Post a correct answer
        resp = c.post(
            reverse('learn.preview', kwargs={'questionid': self.question.id}),
            data={'answer': self.questionoption.id}, follow=True
        )

        self.assertContains(resp, "Well done")

        # Post empty
        resp = c.post(
            reverse('learn.preview', kwargs={'questionid': self.question.id}),
            data={}, follow=True
        )
        self.assertEquals(resp.status_code, 200)

        # Post a incorrect answer
        option = create_test_question_option("wrong", self.question, False)
        resp = c.post(
            reverse('learn.preview', kwargs={'questionid': self.question.id}),
            data={'answer': option.id}, follow=True
        )

        self.assertContains(resp, "Next time")

    def test_right_view_adminpreview(self):

        password = 'mypassword'
        my_admin = CustomUser.objects.create_superuser(
            username='asdf',
            email='asdf@example.com',
            password=password,
            mobile='+27111111111')
        c = Client()
        resp = c.login(username=my_admin.username, password=password)

        self.question = create_test_question(
            'question1',
            self.module,
            question_content='test question')
        self.questionoption = create_test_question_option(
            'questionoption1',
            self.question)

        resp = c.get(
            reverse(
                'learn.preview.right',
                kwargs={
                    'questionid': self.question.id}))

        self.assertContains(resp, "Well done")

    def test_wrong_view_adminpreview(self):

        password = 'mypassword'
        my_admin = CustomUser.objects.create_superuser(
            username='asdf',
            email='asdf@example.com',
            password=password,
            mobile='+27111111111')
        c = Client()
        c.login(username=my_admin.username, password=password)

        self.question = create_test_question(
            'question1',
            self.module,
            question_content='test question',
            state=3)

        self.questionoption = create_test_question_option(
            'questionoption1',
            self.question)

        resp = c.get(
            reverse(
                'learn.preview.wrong',
                kwargs={
                    'questionid': self.question.id}))

        self.assertContains(resp, "Next time")
