"""
conference_helper.py -- Udacity conference server-side Python App Engine
    HTTP controller handlers for memcache & task queue access
    updated by @Robert_Avram on 2015 June 6
"""

import httplib
import endpoints
from google.appengine.ext import ndb

import message_models as mm

import utils


class ConflictException(endpoints.ServiceException):

    """ConflictException -- exception mapped to HTTP 409 response"""
    http_status = httplib.CONFLICT


class WishList(ndb.Model):
    conferences = ndb.KeyProperty(kind="Conference", repeated=True)
    sessions = ndb.KeyProperty(kind='ConferenceSession', repeated=True)

    def to_form(self):
        sessions = ndb.get_multi(self.sessions)
        speaker_keys = []
        for sess in sessions:
            speaker_keys.append(sess.speakerKey)
        speakers = ndb.get_multi(speaker_keys)

        sessions_out = mm.ConferenceSessionForms(
            items=[
                sessions[i].to_form(
                    speakers[i]) for i in range(
                    len(sessions))])

        conferences = ndb.get_multi(self.conferences)
        conferences_out = mm.ConferenceForms(items=[conf.to_form(None) for conf in conferences]
                                             )
        return mm.WishListForm(
            conferences=conferences_out, sessions=sessions_out)


class Profile(ndb.Model):

    """Profile -- User profile object"""
    displayName = ndb.StringProperty()
    mainEmail = ndb.StringProperty()
    teeShirtSize = ndb.StringProperty(default='NOT_SPECIFIED')
    conferenceKeysToAttend = ndb.StringProperty(repeated=True)
    wishList = ndb.LocalStructuredProperty(WishList, default=WishList())


class Conference(ndb.Model):

    """Conference -- Conference object"""
    name = ndb.StringProperty(required=True)
    description = ndb.StringProperty()
    organizerUserId = ndb.StringProperty()
    topics = ndb.StringProperty(repeated=True)
    city = ndb.StringProperty()
    startDate = ndb.DateProperty()
    month = ndb.IntegerProperty()  # TODO: do we need for indexing like Java?
    endDate = ndb.DateProperty()
    maxAttendees = ndb.IntegerProperty()
    seatsAvailable = ndb.IntegerProperty()

    def to_form(self, displayName):
        """Copy relevant fields from Conference to ConferenceForm."""
        cf = mm.ConferenceForm()
        for field in cf.all_fields():
            if hasattr(self, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('Date'):
                    setattr(cf, field.name, str(getattr(self, field.name)))
                else:
                    setattr(cf, field.name, getattr(self, field.name))
            elif field.name == "websafeKey":
                setattr(cf, field.name, self.key.urlsafe())
        if displayName:
            setattr(cf, 'organizerDisplayName', displayName)
        cf.check_initialized()
        return cf


class ConferenceSession(ndb.Model):

    '''Conference Session'''

    name = ndb.StringProperty(required=True)
    type = ndb.StringProperty(default="Typeless")
    startDate = ndb.DateProperty(required=True)
    startTime = ndb.TimeProperty(required=True)
    startTimeSlot = ndb.ComputedProperty(lambda self: self.get_time_slot())
    duration = ndb.IntegerProperty(required=True)
    speakerKey = ndb.KeyProperty(kind='ConferenceSpeaker')
    highlights = ndb.TextProperty()

    def get_time_slot(self):
        return self.startTime.hour

    def to_form(self, speaker):
        csf = mm.ConferenceSessionFormOut()
        for field in csf.all_fields():
            if hasattr(self, field.name):
                if field.name.endswith('Date'):
                    setattr(csf, field.name, str(getattr(self, field.name)))
                elif field.name.endswith('Time'):
                    setattr(csf, field.name, str(getattr(self, field.name)))
                elif field.name == "speakerKey":
                    setattr(csf, field.name, speaker.key.urlsafe())
                else:
                    setattr(csf, field.name, getattr(self, field.name))
            elif field.name == "speakerName":
                setattr(csf, field.name, speaker.displayName)
            elif field.name == "sessionKey":
                setattr(csf, field.name, self.key.urlsafe())
            elif field.name == "confKey":
                setattr(csf, field.name, self.key.parent().urlsafe())
        csf.check_initialized()
        return csf

    @classmethod
    def from_form(cls, mys, parent_key):
        ''' Transform a form into a ConferenceSession object'''

        # copy ConferenceSessionForm/ProtoRPC Message into dict
        REQUIRED_FIELDS = [
            'name',
            'startTime',
            'startDate',
            'duration',
            'speakerKey']
        data = {field.name: getattr(mys, field.name)
                for field in mys.all_fields()}
        del data['websafeConferenceKey']

        # make sure all the required fields are present in the request
        error = filter(lambda x: not data.get(x), REQUIRED_FIELDS)
        if error:
            raise endpoints.BadRequestException(
                ', '.join(error) +
                ' are required')

        try:
            data['startTime'] = utils.make_time(data['startTime'])
            data['startDate'] = utils.make_date(data['startDate'])
        except ValueError:
            raise endpoints.BadRequestException(
                "The date and time need to be properly formated, ex: 2015-12-31, 14:59")

        data['speakerKey'] = ndb.Key(urlsafe=data['speakerKey'])
        data['key'] = parent_key
        return cls(**data)


class ConferenceSpeaker(ndb.Model):

    '''Conference Speaker - Speaker Profile Model'''
    displayName = ndb.StringProperty(required=True)
    conferences = ndb.KeyProperty(kind=Conference, repeated=True)
    conferenceSessions = ndb.KeyProperty(kind=ConferenceSession, repeated=True)

    def to_form(self):
        spf = mm.ConferenceSpeakerFormOut()
        for field in spf.all_fields():
            if field.name == "websafekey":
                setattr(spf, field.name, self.key.urlsafe())
            else:
                setattr(spf, field.name, self.displayName)
        spf.check_initialized()
        return spf
