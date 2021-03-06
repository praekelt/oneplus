from __future__ import division
import logging

from django.conf import settings
from django.shortcuts import redirect, render
from auth.models import Learner
from core.models import Participant, ParticipantBadgeTemplateRel
from gamification.models import GamificationBadgeTemplate
from oneplus.auth_views import resolve_http_method
from oneplus.views import oneplus_check_user
from django.core.urlresolvers import reverse
from oneplus.leaderboard_utils import get_class_leaderboard, get_school_leaderboard, get_national_leaderboard

logger = logging.getLogger(__name__)


def get_learner_label(learner):
    if learner.first_name and learner.last_name:
        return '{0:s} {1:s}'.format(learner.first_name, learner.last_name)
    elif learner.first_name:
        return learner.first_name
    else:
        return 'Anon'

@oneplus_check_user
def badges(request, state, user):
    if not settings.SOCIAL_MEDIA_ACTIVE:
        return redirect('arrive')

    def get():
        badge_id = request.GET.get('b', None)
        participant_id = request.GET.get('p', None)

        learner = None
        participant = None
        if participant_id and Participant.objects.filter(id=participant_id).exists():
            participant = Participant.objects.get(id=participant_id)
            learner = Learner.objects.get(participant__id=participant_id)
            if not learner.public_share:
                learner = None

        if not learner or not learner.public_share:
            return render(request,
                          template_name='public/public_badge.html',
                          dictionary={'no_public': True, 'state': state, 'user': user})

        achieved = False
        badge = None
        if badge_id and GamificationBadgeTemplate.objects.filter(id=badge_id).exists():
            badge = GamificationBadgeTemplate.objects.get(id=badge_id)
            if ParticipantBadgeTemplateRel.objects.filter(participant_id=participant_id,
                                                          badgetemplate_id=badge_id).exists():
                achieved = True
                badge.achieved = True
        else:
            return render(request,
                          template_name='public/public_badge.html',
                          dictionary={'no_public': True, 'state': state, 'user': user})

        fb = {}
        learner_label = get_learner_label(learner)
        if achieved:
            fb['description'] = '{0:s} has earned the {1:s} badge on dig-it!'.format(learner_label, badge.name)

        share_url = '{0:s}?p={1:d}&b={2:d}'.format(reverse('public:badges'), participant.id, badge.id)

        return render(request,
                      template_name='public/public_badge.html',
                      dictionary={'fb': fb,
                                  'badge': badge,
                                  'learner': learner,
                                  'learner_label': learner_label,
                                  'participant': participant,
                                  'state': state,
                                  'share_url': share_url,
                                  'user': user})

    return resolve_http_method(request, [get])


@oneplus_check_user
def level(request, state, user):
    if not settings.SOCIAL_MEDIA_ACTIVE:
        return redirect('arrive')

    def get():
        participant_id = request.GET.get('p', None)

        learner = None
        participant = None
        if participant_id and Participant.objects.filter(id=participant_id).exists():
            participant = Participant.objects.get(id=participant_id)
            learner = Learner.objects.get(participant__id=participant_id)
            if not learner.public_share:
                learner = None

        if not learner or not learner.public_share:
            return render(request,
                          template_name='public/public_level.html',
                          dictionary={'no_public': True, 'state': state, 'user': user})

        learner_label = get_learner_label(learner)

        level, points_remaining = participant.calc_level()
        if level >= settings.MAX_LEVEL:
            level = settings.MAX_LEVEL
            points_remaining = 0

        fb = {'description': '{0:s} has achieved level {1:d} on dig-it!'.format(learner_label, level)}
        share_url = '{0:s}?p={1:d}'.format(reverse('public:level'),
                                           participant.id,)
        return render(request,
                      template_name='public/public_level.html',
                      dictionary={'fb': fb,
                                  'learner': learner,
                                  'learner_label': learner_label,
                                  'level': level,
                                  'levels': range(1, settings.MAX_LEVEL + 1),
                                  'level_max': settings.MAX_LEVEL,
                                  'share_level': share_url,
                                  'participant': participant,
                                  'points_remaining': points_remaining,
                                  'state': state,
                                  'user': user})

    return resolve_http_method(request, [get])


@oneplus_check_user
def leaderboard(request, state, user, board_type=''):
    if not settings.SOCIAL_MEDIA_ACTIVE:
        return redirect('arrive')

    def get():
        participant_id = request.GET.get('p', None)
        max_uncollapsed = 3

        learner = None
        participant = None
        if participant_id and Participant.objects.filter(id=participant_id).exists():
            participant = Participant.objects.get(id=participant_id)
            learner = Learner.objects.get(participant__id=participant_id)
            if not learner.public_share:
                learner = None

        if participant:
            if board_type == 'class':
                share_board = get_class_leaderboard(participant, max_uncollapsed)
            elif board_type == 'school':
                share_board = get_school_leaderboard(participant, max_uncollapsed)
            elif board_type == 'national':
                share_board = get_national_leaderboard(participant, max_uncollapsed)

        if not learner or not learner.public_share:
            return render(request,
                          template_name='public/public_leaderboards.html',
                          dictionary={'no_public': True, 'state': state, 'user': user})

        learner_label = get_learner_label(learner)

        if share_board['type'] != 'school':
            fb = {'description': "{0:s}'s is in {1:d} position on dig-it {2:s} leaderboard!"
                  .format(learner_label, share_board['position'], share_board['type'])}
        else:
            fb = {'description': "{0:s}'s school is in {1:d} position on dig-it {2:s} leaderboard!"
                  .format(learner_label, share_board['position'], share_board['type'])}

        share_url = '{0:s}?p={1:d}'.format(reverse('public:leaderboard', kwargs={'board_type': share_board['type']}),
                                           participant.id)

        return render(request,
                      template_name='public/public_leaderboards.html',
                      dictionary={'fb': fb,
                                  'learner': learner,
                                  'learner_label': learner_label,
                                  'participant': participant,
                                  'share_board': share_board,
                                  'share_level': share_url,
                                  'state': state,
                                  'allow_sharing': participant.learner.public_share,
                                  'user': user})

    return resolve_http_method(request, [get])
