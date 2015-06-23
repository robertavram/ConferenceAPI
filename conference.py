"""
conference.py -- Udacity conference server-side Python App Engine
    HTTP controller handlers for memcache & task queue access

    originally created by wesc on 2014 may 24 by wesc+api@google.com (Wesley Chun)
    
    updated by @Robert_Avram on 2015 June 6

"""


import endpoints
from protorpc import message_types
from protorpc import remote

from google.appengine.api import memcache
from google.appengine.ext import ndb

from models import ConflictException
from models import Profile
from models import Conference

from settings import WEB_CLIENT_ID
from settings import MEMCACHE_ANNOUNCEMENTS_KEY
from settings import ANDROID_CLIENT_ID
from settings import IOS_CLIENT_ID
from settings import ANDROID_AUDIENCE
from settings import MEMCACHE_FEATURED_SPEAKER_KEY

from utils import getUserId

# by @Robert_Avram: - - - - - - - - - - - - -- - - - - - - - - - - - - - - - - - -
# for the separation of concerns, the message classes were moved in messages_models
# all the Messages.message models
import message_models as mm

from models import ConferenceSpeaker
from models import ConferenceSession

# for easier readability and to eliminate confusion all of the helper methods
# are abstracted into ApiHelper class
from conference_helper import ApiHelper

# endby @Robert_Avram - - - -- - - - - - - - - - - - - - - - - - - - - - -

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


@endpoints.api(name='conference', version='v1', audiences=[ANDROID_AUDIENCE],
               allowed_client_ids=[
    WEB_CLIENT_ID,
    API_EXPLORER_CLIENT_ID,
    ANDROID_CLIENT_ID,
    IOS_CLIENT_ID],
    scopes=[EMAIL_SCOPE])
class ConferenceApi(remote.Service, ApiHelper):

    """Conference API v0.1"""

# - - - Conference objects - - - - - - - - - - - - - - - - -

# by @Robert_Avram: - - - - - - - - - - - - -- - - - - - - - - - - - - - - - - - -
    # Removed _copyConferenceToForm(self, conf, displayName) because
    # to_form function was added to the Conference model to replace it.
    # Also replaced all functions that were previously invoking this with the new semantic
    # All helper methods have been moved to ApiHelper
# endby - - - - - - - - - - - - - - - - - - - - - - - -

    @endpoints.method(mm.ConferenceForm, mm.ConferenceForm, path='conference',
                      http_method='POST', name='createConference')
    def createConference(self, request):
        """Create new conference."""
        return self._createConferenceObject(request)

    @endpoints.method(mm.CONF_POST_REQUEST, mm.ConferenceForm,
                      path='conference/{websafeConferenceKey}',
                      http_method='PUT', name='updateConference')
    def updateConference(self, request):
        """Update conference w/provided fields & return w/updated info."""
        return self._updateConferenceObject(request)

    @endpoints.method(mm.CONF_GET_REQUEST, mm.ConferenceForm,
                      path='conference/{websafeConferenceKey}',
                      http_method='GET', name='getConference')
    def getConference(self, request):
        """Return requested conference (by websafeConferenceKey)."""
        # get Conference object from request; bail if not found
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)
        prof = conf.key.parent().get()
        # return ConferenceForm
        # by @Robert_Avram: replaced the self._copyConferenceToForm with
        # conf.to_form
        return conf.to_form(getattr(prof, 'displayName'))

    @endpoints.method(message_types.VoidMessage, mm.ConferenceForms,
                      path='getConferencesCreated',
                      http_method='POST', name='getConferencesCreated')
    def getConferencesCreated(self, request):
        """Return conferences created by user."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # create ancestor query for all key matches for this user
        confs = Conference.query(ancestor=ndb.Key(Profile, user_id))
        prof = ndb.Key(Profile, user_id).get()
        # return set of ConferenceForm objects per Conference
        # by @Robert_Avram: replaced the self._copyConferenceToForm with
        # conf.to_form
        return mm.ConferenceForms(
            items=[
                conf.to_form(
                    getattr(
                        prof,
                        'displayName')) for conf in confs]
        )

    @endpoints.method(mm.ConferenceQueryForms, mm.ConferenceForms,
                      path='queryConferences',
                      http_method='POST',
                      name='queryConferences')
    def queryConferences(self, request):
        """Query for conferences."""
        conferences = self._getQuery(request)

        # need to fetch organiser displayName from profiles
        # get all keys and use get_multi for speed
        organisers = [(ndb.Key(Profile, conf.organizerUserId))
                      for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return individual ConferenceForm object per Conference
        # by @Robert_Avram: replaced the self._copyConferenceToForm with
        # conf.to_form
        return mm.ConferenceForms(
            items=[conf.to_form(names[conf.organizerUserId]) for conf in
                   conferences]
        )


# - - - Profile objects - - - - - - - - - - - - - - - - - - -

    @endpoints.method(message_types.VoidMessage, mm.ProfileForm,
                      path='profile', http_method='GET', name='getProfile')
    def getProfile(self, request):
        """Return user profile."""
        return self._doProfile()

    @endpoints.method(mm.ProfileMiniForm, mm.ProfileForm,
                      path='profile', http_method='POST', name='saveProfile')
    def saveProfile(self, request):
        """Update & return user profile."""
        return self._doProfile(request)


# - - - Announcements - - - - - - - - - - - - - - - - - - - -

    @endpoints.method(message_types.VoidMessage, mm.StringMessage,
                      path='conference/announcement/get',
                      http_method='GET', name='getAnnouncement')
    def getAnnouncement(self, request):
        """Return Announcement from memcache."""
        return mm.StringMessage(
            data=memcache.get(MEMCACHE_ANNOUNCEMENTS_KEY) or "")


# - - - Registration - - - - - - - - - - - - - - - - - - - -

    @ndb.transactional(xg=True)
    def _conferenceRegistration(self, request, reg=True):
        """Register or unregister user for selected conference."""
        retval = None
        prof = self._getProfileFromUser()  # get user Profile

        # check if conf exists given websafeConfKey
        # get conference; check that it exists
        wsck = request.websafeConferenceKey
        conf = ndb.Key(urlsafe=wsck).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)

        # register
        if reg:
            # check if user already registered otherwise add
            if wsck in prof.conferenceKeysToAttend:
                raise ConflictException(
                    "You have already registered for this conference")

            # check if seats avail
            if conf.seatsAvailable <= 0:
                raise ConflictException(
                    "There are no seats available.")

            # register user, take away one seat
            prof.conferenceKeysToAttend.append(wsck)
            conf.seatsAvailable -= 1
            retval = True

        # unregister
        else:
            # check if user already registered
            if wsck in prof.conferenceKeysToAttend:

                # unregister user, add back one seat
                prof.conferenceKeysToAttend.remove(wsck)
                conf.seatsAvailable += 1
                retval = True
            else:
                retval = False

        # write things back to the datastore & return
        prof.put()
        conf.put()
        return mm.BooleanMessage(data=retval)

    @endpoints.method(message_types.VoidMessage, mm.ConferenceForms,
                      path='conferences/attending',
                      http_method='GET', name='getConferencesToAttend')
    def getConferencesToAttend(self, request):
        """Get list of conferences that user has registered for."""
        prof = self._getProfileFromUser()  # get user Profile
        conf_keys = [ndb.Key(urlsafe=wsck)
                     for wsck in prof.conferenceKeysToAttend]
        conferences = ndb.get_multi(conf_keys)

        # get organizers
        organisers = [ndb.Key(Profile, conf.organizerUserId)
                      for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return set of ConferenceForm objects per Conference
        # by @Robert_Avram: replaced the self._copyConferenceToForm with
        # conf.to_form
        return mm.ConferenceForms(items=[conf.to_form(names[conf.organizerUserId])
                                         for conf in conferences]
                                  )

    @endpoints.method(mm.CONF_GET_REQUEST, mm.BooleanMessage,
                      path='conference/{websafeConferenceKey}',
                      http_method='POST', name='registerForConference')
    def registerForConference(self, request):
        """Register user for selected conference."""
        return self._conferenceRegistration(request)

    @endpoints.method(mm.CONF_GET_REQUEST, mm.BooleanMessage,
                      path='conference/{websafeConferenceKey}',
                      http_method='DELETE', name='unregisterFromConference')
    def unregisterFromConference(self, request):
        """Unregister user for selected conference."""
        return self._conferenceRegistration(request, reg=False)

    # - - - - - - - - - - - - removed by @Robert_Avram - - - - - - - - - - - - - - - - - -
    # removed filterPlayground because it had no function anymore
    # - - - - - - - - - - - - end removed - - - - - - - - - - - - - - - - - -


# by @Robert_Avram: - - - - - - - - - - - - -- - - - - - - - - - - - - - -
# - - - -

    @endpoints.method(mm.SESSION_POST_REQUEST, mm.ConferenceSessionFormOut,
                      path="createSession/{websafeConferenceKey}",
                      http_method="POST", name='createSession')
    def createSession(self, request):
        ''' Create Session to Conference, open only to the conference Organizer'''
        return self._createSession(request)

    @endpoints.method(mm.CONF_GET_REQUEST, mm.ConferenceSessionForms,
                      path="getConferenceSessions/{websafeConferenceKey}",
                      http_method="POST", name='getConferenceSessions')
    def getConferenceSessions(self, request):
        ''' Create Session to Conference, open only to the conference Organizer'''

        # get the conference
        confKey = self.get_websafe_key(
            request.websafeConferenceKey,
            "Conference")
        conf = confKey.get()
        if not conf:
            raise endpoints.NotFoundException(
                "The conference you are looking for does not exist")

        # get all the sessions in this conference
        sessions = ConferenceSession.query(ancestor=confKey).fetch(500)

        # make a list with all the speakers at the conferences in order
        speaker_keys = []
        for sess in sessions:
            speaker_keys.append(sess.speakerKey)

        speakers = ndb.get_multi(speaker_keys)
        return mm.ConferenceSessionForms(
            items=[sessions[i].to_form(speakers[i]) for i in range(len(sessions))])

    @endpoints.method(mm.CONF_SESSION_TYPE_REQUEST, mm.ConferenceSessionForms,
                      path="getConferenceSessionsByType/{websafeConferenceKey}",
                      http_method="POST", name='getConferenceSessionsByType')
    def getConferenceSessionsByType(self, request):
        ''' Create Session to Conference, open only to the conference Organizer'''

        # Limit the amount of types one can include:
        if len(request.typeOfSession) > 5:
            raise endpoints.BadRequestException(
                "Maximum number of typeOfSession to include is 5")

        # get the conference
        confKey = self.get_websafe_key(
            request.websafeConferenceKey,
            "Conference")
        conf = confKey.get()
        if not conf:
            raise endpoints.BadRequestException(
                "This conference does not exist: %s" %
                confKey)

        # query ConferenecSession
        q = ConferenceSession.query(ancestor=confKey)

        types = request.typeOfSession
        if types:
            q = q.filter(ConferenceSession.type.IN(types))
        q = q.order(ConferenceSession.name)
        sessions = q.fetch(100)
        speaker_keys = []
        for sess in q:
            speaker_keys.append(sess.speakerKey)
        speakers = ndb.get_multi(speaker_keys)

        return mm.ConferenceSessionForms(
            items=[sessions[i].to_form(speakers[i]) for i in range(len(sessions))])

    @endpoints.method(mm.SPEAKER_SESSION_GET_REQUEST, mm.ConferenceSessionForms,
                      path="getSessionsBySpeaker/{websafeSpeakerKey}",
                      http_method="GET", name='getSessionsBySpeaker')
    def getSessionsBySpeaker(self, request):
        '''Given a speaker, return all sessions given by this particular speaker, across all conferences'''

        speaker_key = self.get_websafe_key(
            request.websafeSpeakerKey,
            "ConferenceSpeaker")
        speaker = speaker_key.get()
        if not speaker:
            raise endpoints.NotFoundException(
                "The speaker you are looking for was not found!")

        sessions = ndb.get_multi(speaker.conferenceSessions)

        return mm.ConferenceSessionForms(
            items=[sessions[i].to_form(speaker) for i in range(len(sessions))])

    @endpoints.method(mm.ConferenceSpeakerForm, mm.ConferenceSpeakerFormOut,
                      path="registerSpeaker",
                      http_method="POST", name='registerSpeaker')
    def registerSpeaker(self, request):
        ''' Register Conference Speaker '''
        return self._registerSpeaker(request)

    @endpoints.method(mm.SESSION_GET_REQUEST, mm.BooleanMessage,
                      path="addSessionToWishlist/{websafeSessionKey}",
                      http_method="POST", name='addSessionToWishlist')
    def addSessionToWishlist(self, request):
        ''' Register Conference Speaker'''
        return mm.BooleanMessage(data=self._add_session_to_wishlist(request))

    @endpoints.method(message_types.VoidMessage, mm.ConferenceSpeakerForms,
                      path="getSpeakers",
                      http_method="POST", name='getSpeakers')
    def getSpeakers(self, unused_request):
        ''' Get some Conference Speakers - this is a helper method
        to query for some speakers in order to retrieve speaker keys -for testing purposes only'''
        # query ConferenceSpeakers and get the first 100 records
        speakers = ConferenceSpeaker.query().fetch(100)
        return mm.ConferenceSpeakerForms(
            items=[speaker.to_form() for speaker in speakers])

    @endpoints.method(mm.GET_SPEAKERS_BY_NAME, mm.ConferenceSpeakerForms,
                      path="getSpeakersByName",
                      http_method="POST", name='getSpeakersByName')
    def getSpeakersByName(self, request):
        '''Given the full displayName of a speaker get Conference Speakers with that name'''
        # ConferenceSpeaker allows for multiple speakers to have the same name,
        # eventually by adding more characteristics to the speaker we will be able to query more specifically
        # for now, return the first 10 of that name we encounter.
        speakers = ConferenceSpeaker.query(
            ConferenceSpeaker.displayName == request.displayName).fetch(10)
        return mm.ConferenceSpeakerForms(
            items=[speaker.to_form() for speaker in speakers])

    @endpoints.method(message_types.VoidMessage, mm.WishListForm,
                      path="getSessionsInWishList",
                      http_method="POST", name='getSessionsInWishList')
    def getSessionsInWishList(self, request):
        '''Get the sessions and the conferences in wish list of the current user'''
        return self._get_wishlist()

    @endpoints.method(mm.REMOVE_SESSION_POST_REQUEST, mm.BooleanMessage,
                      path="removeSessionFromWishList",
                      http_method="POST", name='removeSessionFromWishList')
    def removeSessionFromWishList(self, request):
        '''Removes a session from the current user's wish list -
        takes in websafeSessionKey and removeConference bool if
        the user wishes to also remove the conference from the wishlist '''
        return mm.BooleanMessage(data=self._remove_session_from_wishlist(
            request.websafeSessionKey, request.removeConference))

    @endpoints.method(mm.QUERY_PROBLEM, mm.ConferenceSessionForms,
                      path="queryproblem",
                      http_method="GET", name='queryproblem')
    def queryproblem(self, request):
        '''first solution for the query problem
        takes in:
            afterTime - the hour block after which a user is unavailable
                        eg: 19 (for 7PM) - type(int);
            exclude - types of sessions to exclude (max 3) type(str)'''
        return self._queryproblem(request)

    @endpoints.method(mm.QUERY_PROBLEM2, mm.ConferenceSessionForms_search,
                      path="queryproblem2",
                      http_method="GET", name='queryproblem2')
    def queryproblem2(self, request):
        ''' Searches for sessions between after or before certain times, excludes or includes certain types,
        allows text search for highlights specifically, or general search terms that
        might be found in session type, name, conference name, speaker name, conference description,
        limitations: max 3 excludes or includes'''

        return mm.ConferenceSessionForms_search(
            items=self._queryproblem2(request))

    @endpoints.method(mm.SPEAKER_SESSION_GET_REQUEST, mm.ConferenceForms,
                      path="getConferencesBySpeaker",
                      http_method="GET", name='getConferencesBySpeaker')
    def getConferencesBySpeaker(self, request):
        '''Given a speaker, returns all conferences that they will speak in'''

        speaker_key = self.get_websafe_key(
            request.websafeSpeakerKey,
            "ConferenceSpeaker")
        speaker = speaker_key.get()
        if not speaker:
            raise endpoints.NotFoundException(
                "The speaker you are looking for was not found!")

        conferences = ndb.get_multi(speaker.conferences)

        return mm.ConferenceForms(
            items=[conf.to_form(None) for conf in conferences])

    @endpoints.method(mm.GET_SESSIONS_BY_SPEAKER_CONFERENCE, mm.ConferenceSessionForms,
                      path="getSessionsFromSpeakerAndConference",
                      http_method="GET", name='getSessionsFromSpeakerAndConference')
    def getSessionsFromSpeakerAndConference(self, request):
        '''Given a speaker and a conference return all sessions that have that speaker'''
        # get speaker key and make sure we have a speaker
        speaker_key = self.get_websafe_key(
            request.websafeSpeakerKey,
            "ConferenceSpeaker")
        speaker = speaker_key.get()
        if not speaker:
            raise endpoints.NotFoundException(
                "The speaker you are looking for was not found!")

        # get conference key and make sure we have a conference
        conf_key = self.get_websafe_key(
            request.websafeConferenceKey,
            "Conference")
        conference = conf_key.get()
        if not conference:
            raise endpoints.NotFoundException(
                "The conference you are looking for was not found!")

        q = ConferenceSession.query(ancestor=conf_key)
        q = q.filter(ConferenceSession.speakerKey == speaker_key)

        sessions = q.fetch(50)

        return mm.ConferenceSessionForms(
            items=[sessions[i].to_form(speaker) for i in range(len(sessions))])

    @endpoints.method(message_types.VoidMessage, mm.FeaturedSpeakerForm,
                      path="getFeaturedSpeaker",
                      http_method="GET", name='getFeaturedSpeaker')
    def getFeaturedSpeaker(self, request):
        '''Get featured speaker'''
        fs = memcache.get(MEMCACHE_FEATURED_SPEAKER_KEY)
        if not fs:
            return mm.FeaturedSpeakerForm()
        return mm.FeaturedSpeakerForm(name=fs.get('name'),
                                      sessions=fs.get('sessions'),
                                      conference=fs.get('conf'),
                                      conference_location=fs.get('conf_loc'))

# - - - - - - - - - - - - end added_by @Robert_Avram- - - - - - - - - - - - - - - - - -


api = endpoints.api_server([ConferenceApi])  # register API
