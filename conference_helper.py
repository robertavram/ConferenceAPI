"""
conference_helper.py -- Udacity conference server-side Python App Engine
    HTTP controller handlers for memcache & task queue access
    created by @Robert_Avram on 2015 June 6
"""


import endpoints
from google.appengine.ext import ndb
from google.appengine.api import search
from google.appengine.api import taskqueue
from google.appengine.api import memcache
from google.net.proto.ProtocolBuffer import ProtocolBufferDecodeError
from webapp2 import cached_property

from models import Conference
from models import ConferenceSession
from models import ConferenceSpeaker
from models import Profile

from settings import MEMCACHE_ANNOUNCEMENTS_KEY
from settings import MEMCACHE_FEATURED_SPEAKER_KEY
from settings import ANNOUNCEMENT_TPL
from settings import DEFAULTS
from settings import OPERATORS
from settings import FIELDS

import message_models as mm 

import logging
import utils
from datetime import datetime


def user_required(handler):
    """Decorator that checks if there's a user associated with the current session."""
    def check_login(self, *args, **kwargs):
        # Make sure there is a user authenticated
        if not self.auth_user:
            raise endpoints.UnauthorizedException('Authorization Required')
        
        
        # Make sure the current user has a profile in our DB
        if not self.user:
            raise endpoints.UnauthorizedException('Even though you are authorized, you do not have a Profile \
                                please update your account first, Profile Required')
        else:
            return handler(self, *args, **kwargs)

    return check_login

class BaseHandler(object):
    ''' Basic Handler functions that can be inherited by any api '''
    @cached_property
    def user(self):
        ''' helper function that computes and caches current user profile
        relies on auth_user, returns Profile or None'''
        
        # check if there is a current user logged in
        if self.auth_user:
            # get user_id of current logged in auth_user
            user_id = utils.getUserId(self.auth_user)
            p_key = ndb.Key(Profile, user_id)
            # get Profile from datastore
            return p_key.get()
        else:
            return None
    
    @cached_property
    def auth_user(self):
        ''' helper function that computes and caches current_user '''
        return endpoints.get_current_user()
    
    
    
class ApiHelper(BaseHandler):
    ''' Class meant to help the conference Api. Base: BaseHandler '''
    
    @staticmethod
    def get_websafe_key(urlsafeKey, modelkind):
        ''' takes a urlsafeKey and the kind of key it should be and 
        returns the ndb.Key or raises a BadRequest Error if the key
        is not the propper format or not the right kind '''
        try:
            s_key = ndb.Key(urlsafe=urlsafeKey)
        except ProtocolBufferDecodeError:
            raise endpoints.BadRequestException('the key received is not a valid urlsafe key')
        if (not s_key) or (not s_key.kind() == modelkind):
            raise endpoints.BadRequestException('the key valid key for the kind %s'%modelkind)
        return s_key
    
    @user_required
    def _add_session_to_wishlist(self, request):
        ''' adds a session to the user's wishlist '''
        
        # make sure that the websafeSessionKey is actually valid
        s_key = self.get_websafe_key(request.websafeSessionKey, 'ConferenceSession')
        
        # check if the session exists in the db   
        session = s_key.get()
        if not session:
            raise endpoints.NotFoundException('The session you want to add does not exist')
               
        # make sure the keys are not in the wishList already
        if session.key.parent() not in self.user.wishList.conferences:
            # if this conference doesn't exist in the wishList,
            # add it since the session belongs to it
            self.user.wishList.conferences.append(session.key.parent())
            # this also implies that this session does not exist in the wishList
            self.user.wishList.sessions.append(session.key)
            self.user.put()
        elif session.key not in self.user.wishList.sessions:
            self.user.wishList.sessions.append(session.key)
            self.user.put()
        else:
            raise endpoints.BadRequestException('the session is already in the wish list')
        
        return True
    
    def _query_index(self, qry):
        ''' Query the search index for sessions, 
        takes in search.Query '''
        # Query the index.
        index = search.Index(name='sessions')
        try:
            results = index.search(qry)
        
            # Iterate through the search results.
            items = []
            for scored_document in results:
                items.append(self._copy_session_doc_to_form(scored_document))
                
        except search.Error, e:
            logging.error(e)
            
        return items
    
    def _add_to_search_index(self, session, speaker, conference):
        ''' Create a search document based on session, speaker and conference,
        and added to the search index '''
        # define the index
        index = search.Index(name='sessions')
        
        #create the document object
        doc = search.Document(
            # the doc_id will be set to the key of the session
            doc_id = session.key.urlsafe(),
            fields=[
                    search.TextField(name='name', value=session.name),
                    search.TextField(name='type', value=session.type),
                    search.NumberField(name='duration', value=session.duration),
                    search.DateField(name="startDate", value=session.startDate),
                    search.NumberField(name="startTime", value=utils.time_to_minutes(session.startTime)),
                    search.TextField(name='highlights', value=session.highlights),
                    search.TextField(name='speakerName', value=speaker.displayName),
                    search.TextField(name='conferenceName', value=conference.name),
                    search.TextField(name='conferenceTopics', value=" ".join([topic for topic in conference.topics])),
                    search.TextField(name='conferenceCity', value=conference.city),
                    search.TextField(name='conferenceDescription', value=conference.description),
                    ])
        
        try:
            index.put(doc)
        except search.PutError, e:
            result = e.results[0]
            if result.code == search.OperationResult.TRANSIENT_ERROR:
                # if TRANSIENT_ERROR retry:
                try:
                    index.put(result.object_id)
                except search.Error, e:
                    logging.error(e)
        except search.Error, e:
            logging.error(e)
    
    @user_required
    def _remove_session_from_wishlist(self, conf_sessionKey, removeConference=False):
        ''' Removes a session from the wishList '''
        # make sure that the websafeSessionKey is actually valid
        s_key = self.get_websafe_key(conf_sessionKey, 'ConferenceSession')
        # check if the session exists in the db   
        session = s_key.get()
        if not session:
            raise endpoints.NotFoundException('The session you want to add does not exist')
        
        # if key is in the wishList remove it otherwise BadRequestException
        if session.key in self.user.wishList.sessions:
            self.user.wishList.sessions.remove(session.key)
        else:
            raise endpoints.BadRequestException('the session is not in the wish list')
        
        # if the user wants to remove the conference as well
        if removeConference:
            # check if there are any other sessions in the wishlist with the same conference
            for sesskey in self.user.wishList.sessions:
                if sesskey.parent() == session.key.parent():
                    raise endpoints.ConflictException("cannot remove conference because there are other sessions from this conference in the wish list")
            self.user.wishList.conferences.remove(session.key.parent())
        
        self.user.put()
        return True
            
    # cross-group needed because the speaker is not related to the session
    @ndb.transactional(xg=True)
    def _putSessionAndSpeaker(self, my_session, conf, speaker):
        ''' transactional put for session and speaker '''
        my_session.put()
        if conf.key not in speaker.conferences:
            speaker.conferences.append(conf.key)
        speaker.conferenceSessions.append(my_session.key)
        speaker.put()
        return (my_session, conf, speaker)
    
    @user_required
    def _get_wishlist(self):
        return self.user.wishList.to_form()
    
    @user_required    
    def _createSession(self, request):
        '''creates a ConferenceSession, adds it as a child of the conference, returns the stored object'''
      
        # make sure the speakerKey is for a valid speaker
        speaker_key = self.get_websafe_key(request.speakerKey, "ConferenceSpeaker")
        speaker = speaker_key.get()
        
        # make sure there the speaker exists in the DB
        if not speaker:
            raise endpoints.NotFoundException(
                    "The speaker you requested was not found, \
                    Please register a speaker first")
            
        # get Conference from the DB
        wsck = self.get_websafe_key(request.websafeConferenceKey, "Conference")
        conf = wsck.get()
        # make sure conference exists and that it belongs to current user
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)
        if not conf.key.parent() == self.user.key:
            raise endpoints.ForbiddenException('This conference was organized by a different user')
        
        # get a key for the new session
        s_id = ConferenceSession.allocate_ids(size=1, parent=conf.key)[0]
        session_key = ndb.Key(ConferenceSession, s_id, parent=conf.key)
        
        # put the session in the db and update conference
        my_session = ConferenceSession.from_form(request, session_key)
        
        #TODO: make sure that the session times fall between the conference times
        
        
        # check if speaker already has a session within this conference
        if conf.key in speaker.conferences:
            # if yes retrieve the all the other session names for this speaker in this conference
            # note the current session is not included because we don't want to retrieve it again, we can just pass the name
            sessions_in_conference = [skey.urlsafe() for skey in speaker.conferenceSessions if skey.parent() == conf.key]
            # make this a featured speaker for this conference, 
            # as asked in task 4 of the project setting up a task to do this.
            taskqueue.add(params={"speaker_name": speaker.displayName,
                                  "sess_keys": sessions_in_conference,
                                  "current_sess_name": my_session.name,
                                  "conf": conf.name,
                                  "conf_loc": conf.city},
                          url='/tasks/add_featured_speaker')
            
        
        # use a transactional to make the updates
        # current function would not allow a transactional because of the id allocation
        self._putSessionAndSpeaker(my_session, conf, speaker)
        
        # create an indexed document for the search API based on this session
        self._add_to_search_index(my_session, speaker, conf)
        
        return my_session.to_form(speaker)
    
    @staticmethod
    def _setFeaturedSpeaker(speaker_name, sess_keys, current_sess_name, conf, conf_loc):
        ''' Sets the featured speaker in memchace '''
        
        # get the sessions from sess_keys, we can assume that the sess_keys are valid since they 
        # are passed by the task
        sessions = ndb.get_multi([ndb.Key(urlsafe=sk) for sk in sess_keys])
        s_names = [s.name for s in sessions]
        s_names.append(current_sess_name)
        memcache.set(key=MEMCACHE_FEATURED_SPEAKER_KEY, value={"name": speaker_name,
                                                   "sessions": s_names,
                                                   "conf": conf,
                                                   "conf_loc": conf_loc})
         
    
    
    @user_required
    def _registerSpeaker(self, request):
        '''registers a speaker, user needs to be logged in and conference organizer to register a speaker''' 
        # make sure the displayName received is valid format
        if not utils.is_valid_name(request.displayName):
            raise endpoints.BadRequestException("displayName is not valid: it must be between 3 and 50 characters with no special characters and title case")
        # make sure user is has organizer privileges or has organized at least one conference
        cnt = Conference.query(ancestor=self.user.key).count(limit=1)
        if not cnt:
            raise endpoints.ForbiddenException("You need to have organized at least one conference in order to register speakers")
        
        speaker = ConferenceSpeaker(displayName=request.displayName)
        speaker.put()
        return speaker.to_form()
    
    def _queryproblem(self, request):
        ''' session query method to search for unavailable after a certain time (in int hour blocks)
        and exclude up to 3 types of sessions '''
        
        # to reduce friction we will only allow 3 excludes
        if len(request.exclude)>3:
            raise endpoints.BadRequestException("You are only allowed to exclude up to 3 types of Sessions.")
        
        # list of all allowed timeslots
        # ideally this list is created in order from the most popular session times
        allowed_timeslots = [i for i in range(24)]
        # compose a list of unavailable times
        if request.afterTime:
            dissalowed_timeslots = [i for i in xrange(request.afterTime,24)]
        else:
            dissalowed_timeslots = []
        
        # exclude dissalowedtimeslots
        query_times = [i for i in allowed_timeslots if i not in dissalowed_timeslots]
        q = ConferenceSession.query()
        q = q.filter(ConferenceSession.startTimeSlot.IN(query_times))
        
                
        # filter out all excludes
        for s_type in request.exclude:
            q = q.filter(ConferenceSession.type != s_type)
        
        # order by conference type first since that is the inequality filter
        q.order(ConferenceSession.type)
        q.order(ConferenceSession.startTime)
        
        # fetch max 100 records
        sessions = q.fetch(100)
        
        
        speaker_keys = []
        for sess in q:
            speaker_keys.append(sess.speakerKey)
        # get speakers for every session in order
        speakers = ndb.get_multi(speaker_keys)
        return mm.ConferenceSessionForms(items=[sessions[i].to_form(speakers[i]) for i in range(len(sessions))])
    
    def _copy_session_doc_to_form(self, doc):
        ''' copies a ScoredDocument to ConferenceSessionForm_search '''
        form_out = mm.ConferenceSessionForm_search()
        setattr(form_out, "websafeSessionKey", doc.doc_id)
        for field in doc.fields:
            if isinstance(field, search.NumberField):
                if field.name == "startTime":
                    setattr(form_out, field.name, utils.minutes_to_timestring(int(field.value)))
                    continue
                setattr(form_out, field.name, int(field.value))
            elif isinstance(field, search.DateField):
                setattr(form_out, field.name, str(field.value))
            else:
                setattr(form_out, field.name, field.value)
        
        form_out.check_initialized()
        
        return form_out

    
    def _queryproblem2(self, request):
        ''' use the search API to query for specific sessions '''
        
        # only allow up to 3 excludes and 3 includes
        if len(request.exclude_types) > 3 or len(request.include_types)> 3:
            raise endpoints.BadRequestException("you can only exclude or include max 3 types")
        
        # limit the length of the search fields that someone sends
        if (request.search_highlights and len(request.search_highlights) > 50)\
           or (request.search_general and len(request.search_general) > 50):
            raise endpoints.BadRequestException("your search query strings can only be up to 50 characters, longer blocks are useless anyway")
        
        # start forming the query string qs
        qs = ''
        
        # check if the variables were passed in and update the qs accordingly
        if request.before_time:
            qs += 'startTime < '+str(utils.time_to_minutes(request.before_time))
        if request.after_time:
            qs += ' startTime > '+str(utils.time_to_minutes(request.after_time))
        
        if request.exclude_types:
            qs += " NOT type: ("
            for i in range(len(request.exclude_types)):
                qs += utils.clean_s(request.exclude_types[i])
                if not i == len(request.exclude_types)-1:
                    qs += " OR "
                    continue
                qs += ")"
                
        if request.include_types:
            qs += " type: ("
            for i in range(len(request.include_types)):
                qs += utils.clean_s(request.include_types[i])
                if not i == len(request.include_types)-1:
                    qs += " OR "
                    continue
                qs += ")"
                    
        if request.search_highlights:
            qs += " highlights:" + utils.clean_s(request.search_highlights)
        
        if request.search_general:
            qs += " " + utils.clean_s(request.search_general)
        
        # add some sorting options
        sort1 = search.SortExpression(expression='startDate', direction=search.SortExpression.ASCENDING, default_value=0)
        # compose the sort options
        # attn: Using match_scorer is more expensive to run but it sorts the documents based on relevance better.
        sort_opts = search.SortOptions(expressions=[sort1], match_scorer=search.MatchScorer())
        
        # add some query options, limit on 25 results
        query_options = search.QueryOptions(
            limit=25,
            sort_options= sort_opts)
        
        # compose the query
        qry= search.Query(query_string=qs, options=query_options)
        return self._query_index(qry)
    
###  PREVIOUSLY EXISTING METHODS - - - -  - - - - - -  - - - - - - - - -  - - - - - - - - - 

    @staticmethod
    def _cacheAnnouncement():
        """Create Announcement & assign to memcache; used by
        memcache cron job & putAnnouncement().
        """
        confs = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0)
        ).fetch(projection=[Conference.name])

        if confs:
            # If there are almost sold out conferences,
            # format announcement and set it in memcache
            announcement = ANNOUNCEMENT_TPL % (
                ', '.join(conf.name for conf in confs))
            memcache.set(MEMCACHE_ANNOUNCEMENTS_KEY, announcement)
        else:
            # If there are no sold out conferences,
            # delete the memcache announcements entry
            announcement = ""
            memcache.delete(MEMCACHE_ANNOUNCEMENTS_KEY)

        return announcement
    def _createConferenceObject(self, request):
        """Create or update Conference object, returning ConferenceForm/request."""
        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = utils.getUserId(user)

        if not request.name:
            raise endpoints.BadRequestException("Conference 'name' field required")

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}
        del data['websafeKey']
        del data['organizerDisplayName']

        # add default values for those missing (both data model & outbound Message)
        for df in DEFAULTS:
            if data[df] in (None, []):
                data[df] = DEFAULTS[df]
                setattr(request, df, DEFAULTS[df])

        # convert dates from strings to Date objects; set month based on start_date
        if data['startDate']:
            data['startDate'] = datetime.strptime(data['startDate'][:10], "%Y-%m-%d").date()
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(data['endDate'][:10], "%Y-%m-%d").date()

        # set seatsAvailable to be same as maxAttendees on creation
        if data["maxAttendees"] > 0:
            data["seatsAvailable"] = data["maxAttendees"]
        # generate Profile Key based on user ID and Conference
        # ID based on Profile key get Conference key from ID
        p_key = ndb.Key(Profile, user_id)
        c_id = Conference.allocate_ids(size=1, parent=p_key)[0]
        c_key = ndb.Key(Conference, c_id, parent=p_key)
        data['key'] = c_key
        data['organizerUserId'] = request.organizerUserId = user_id

        # create Conference, send email to organizer confirming
        # creation of Conference & return (modified) ConferenceForm
        Conference(**data).put()
        taskqueue.add(params={'email': user.email(),
            'conferenceInfo': repr(request)},
            url='/tasks/send_confirmation_email'
        )
        return request

    @ndb.transactional()
    def _updateConferenceObject(self, request):
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = utils.getUserId(user)

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}

        # update existing conference
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)

        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the conference.')

        # Not getting all the fields, so don't create a new object; just
        # copy relevant fields from ConferenceForm to Conference object
        for field in request.all_fields():
            data = getattr(request, field.name)
            # only copy fields where we get data
            if data not in (None, []):
                # special handling for dates (convert string to Date)
                if field.name in ('startDate', 'endDate'):
                    data = datetime.strptime(data, "%Y-%m-%d").date()
                    if field.name == 'startDate':
                        conf.month = data.month
                # write to Conference object
                setattr(conf, field.name, data)
        conf.put()
        prof = ndb.Key(Profile, user_id).get()
        # by @Robert_Avram: replaced the self._copyConferenceToForm with conf.to_form
        return conf.to_form(getattr(prof, 'displayName'))
    
    def _getQuery(self, request):
        """Return formatted query from the submitted filters."""
        q = Conference.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Conference.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Conference.name)
            
        filters = sorted(filters, key=lambda k: k['field'])
        
        for filtr in filters:
            if filtr["field"] in ["month", "maxAttendees"]:
                filtr["value"] = int(filtr["value"])
            formatted_query = ndb.query.FilterNode(filtr["field"], filtr["operator"], filtr["value"])
            q = q.filter(formatted_query)
        return q


    def _formatFilters(self, filters):
        """Parse, check validity and format user supplied filters."""
        
        current_fields = []
        formatted_filters = []
        inequality_field = None

        for f in filters:
            filtr = {field.name: getattr(f, field.name) for field in f.all_fields()}

            try:
                filtr["field"] = FIELDS[filtr["field"]]
                filtr["operator"] = OPERATORS[filtr["operator"]]
            except KeyError:
                raise endpoints.BadRequestException("Filter contains invalid field or operator.")

            # Every operation except "=" is an inequality
            if filtr["operator"] != "=":
                # check if inequality operation has been used in previous filters
                # disallow the filter if inequality was performed on a different field before
                # track the field on which the inequality operation is performed
                if inequality_field and inequality_field != filtr["field"]:
                    raise endpoints.BadRequestException("Inequality filter is allowed on only one field.")
                elif filtr["field"] in ["city", "topics"]:
                    raise endpoints.BadRequestException("Inequality filter not allowed on city or topics.")
                else:
                    inequality_field = filtr["field"]
                    
            if filtr["field"] in current_fields:
                raise endpoints.BadRequestException("You cannot query multiple fields of one type, %s"%filtr['field'])
            current_fields.append(filtr['field'])
            formatted_filters.append(filtr)
        return (inequality_field, formatted_filters)
    
    # - - - Profile objects - - - - - - - - - - - - - - - - - - -

    #TODO: replace _copyProfileToForm with a to_form method on the Profile model
    def _copyProfileToForm(self, prof):
        """Copy relevant fields from Profile to ProfileForm."""
        # copy relevant fields from Profile to ProfileForm
        pf = mm.ProfileForm()
        for field in pf.all_fields():
            if hasattr(prof, field.name):
                # convert t-shirt string to Enum; just copy others
                if field.name == 'teeShirtSize':
                    setattr(pf, field.name, getattr(mm.TeeShirtSize, getattr(prof, field.name)))
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf


    def _getProfileFromUser(self):
        """Return user Profile from datastore, creating new one if non-existent."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get Profile from datastore
        user_id = utils.getUserId(user)
        p_key = ndb.Key(Profile, user_id)
        profile = p_key.get()
        # create new Profile if not there
        if not profile:
            profile = Profile(
                key = p_key,
                displayName = user.nickname(),
                mainEmail= user.email(),
                teeShirtSize = str(mm.TeeShirtSize.NOT_SPECIFIED),
            )
            profile.put()

        return profile      # return Profile
  
    def _doProfile(self, save_request=None):
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
        prof = self._getProfileFromUser()

        # if saveProfile(), process user-modifyable fields
        if save_request:
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    val = getattr(save_request, field)
                    if val:
                        setattr(prof, field, str(val))
                        #if field == 'teeShirtSize':
                        #    setattr(prof, field, str(val).upper())
                        #else:
                        #    setattr(prof, field, val)
                        prof.put()

        # return ProfileForm
        return self._copyProfileToForm(prof)
    
    
    
    
    
    
    
    
    
    
    