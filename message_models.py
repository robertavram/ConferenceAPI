"""
message_models.py -- Udacity conference server-side Python App Engine
    HTTP controller handlers for memcache & task queue access
    created by @Robert_Avram on 2015 June 6
"""


import endpoints
from protorpc import messages
from protorpc import message_types



class ProfileMiniForm(messages.Message):
    """ProfileMiniForm -- update Profile form message"""
    displayName = messages.StringField(1)
    teeShirtSize = messages.EnumField('TeeShirtSize', 2)

class ProfileForm(messages.Message):
    """ProfileForm -- Profile outbound form message"""
    displayName = messages.StringField(1)
    mainEmail = messages.StringField(2)
    teeShirtSize = messages.EnumField('TeeShirtSize', 3)
    conferenceKeysToAttend = messages.StringField(4, repeated=True)

class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    data = messages.StringField(1, required=True)

class BooleanMessage(messages.Message):
    """BooleanMessage-- outbound Boolean value message"""
    data = messages.BooleanField(1)
    
class ConferenceSessionForm(messages.Message):
    '''ConferenceSession - ConferenceSessions in/outbound form messages'''
    name            = messages.StringField(1)
    type            = messages.StringField(2)
    duration        = messages.IntegerField(3)
    startDate       = messages.StringField(4)
    startTime       = messages.StringField(5)
    highlights      = messages.StringField(6)
    speakerKey      = messages.StringField(7)
    
class ConferenceSessionFormOut(messages.Message):
    '''ConferenceSession - ConferenceSessions in/outbound form messages'''
    name            = messages.StringField(1)
    type            = messages.StringField(2)
    duration        = messages.IntegerField(3)
    startDate       = messages.StringField(4)
    startTime       = messages.StringField(5)
    highlights      = messages.StringField(6)
    speakerKey      = messages.StringField(7)
    speakerName     = messages.StringField(8)
    sessionKey      = messages.StringField(9)
    confKey         = messages.StringField(10)
    
class ConferenceSessionForm_search(messages.Message):
    '''ConferenceSession - ConferenceSessions in/outbound form messages'''
    websafeSessionKey = messages.StringField(1)
    name            = messages.StringField(2)
    type            = messages.StringField(3)
    duration        = messages.IntegerField(4)
    startDate       = messages.StringField(5)
    startTime       = messages.StringField(6)
    highlights      = messages.StringField(7)
    speakerName     = messages.StringField(8)
    conferenceName  = messages.StringField(9)
    conferenceTopics = messages.StringField(10)
    conferenceCity  = messages.StringField(11)
    conferenceDescription = messages.StringField(12)
    
class ConferenceSessionForms(messages.Message):
    """ConferenceSessionForms -- multiple ConferenceSession form message"""
    items = messages.MessageField(ConferenceSessionFormOut, 1, repeated=True)

class ConferenceSessionForms_search(messages.Message):
    """ConferenceSessionForms -- multiple ConferenceSession form message"""
    items = messages.MessageField(ConferenceSessionForm_search, 1, repeated=True)
    
    

    
class ConferenceSpeakerForm(messages.Message):
    '''Conference Speaker - Speaker Profile form message'''
    displayName = messages.StringField(1)

class ConferenceSpeakerFormOut(messages.Message):
    '''Conference Speaker - Speaker Profile form message'''
    displayName = messages.StringField(1)
    websafekey = messages.StringField(2)
    
class ConferenceSpeakerForms(messages.Message):
    '''Conference Speaker - Speaker Profile form message'''
    items = messages.MessageField(ConferenceSpeakerFormOut, 1, repeated=True)
    
class ConferenceForm(messages.Message):
    """ConferenceForm -- Conference outbound form message"""
    name            = messages.StringField(1)
    description     = messages.StringField(2)
    organizerUserId = messages.StringField(3)
    topics          = messages.StringField(4, repeated=True)
    city            = messages.StringField(5)
    startDate       = messages.StringField(6) #DateTimeField()
    month           = messages.IntegerField(7)
    maxAttendees    = messages.IntegerField(8)
    seatsAvailable  = messages.IntegerField(9)
    endDate         = messages.StringField(10) #DateTimeField()
    websafeKey      = messages.StringField(11)
    organizerDisplayName = messages.StringField(12)
    
    
class ConferenceForms(messages.Message):
    """ConferenceForms -- multiple Conference outbound form message"""
    items = messages.MessageField(ConferenceForm, 1, repeated=True)
    
    
class WishListForm(messages.Message):
    ''' WhishListForms - repr conferences and sessionslists '''
    conferences = messages.MessageField(ConferenceForms, 1)
    sessions = messages.MessageField(ConferenceSessionForms, 2)
    
class TeeShirtSize(messages.Enum):
    """TeeShirtSize -- t-shirt size enumeration value"""
    NOT_SPECIFIED = 1
    XS_M = 2
    XS_W = 3
    S_M = 4
    S_W = 5
    M_M = 6
    M_W = 7
    L_M = 8
    L_W = 9
    XL_M = 10
    XL_W = 11
    XXL_M = 12
    XXL_W = 13
    XXXL_M = 14
    XXXL_W = 15

class ConferenceQueryForm(messages.Message):
    """ConferenceQueryForm -- Conference query inbound form message"""
    field = messages.StringField(1)
    operator = messages.StringField(2)
    value = messages.StringField(3)

class ConferenceQueryForms(messages.Message):
    """ConferenceQueryForms -- multiple ConferenceQueryForm inbound form message"""
    filters = messages.MessageField(ConferenceQueryForm, 1, repeated=True)
    
class FeaturedSpeakerForm(messages.Message):
    """ConferenceQueryForms -- multiple ConferenceQueryForm inbound form message"""
    name                 = messages.StringField(1)
    conference           = messages.StringField(2)
    conference_location  = messages.StringField(3)
    sessions             = messages.StringField(4, repeated=True)
    
    
# - - - - - - - - - - - Resource Containers - - - - - - - - - - - - - - - - - - - - - - - 
CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)
CONF_POST_REQUEST = endpoints.ResourceContainer(
    ConferenceForm,
    websafeConferenceKey=messages.StringField(1),
)

# - - - - - - - - - - - - added by @Robert_Avram - - - - - - - - - - - - - - - - - -
SPEAKER_SESSION_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeSpeakerKey=messages.StringField(1),
)
GET_SESSIONS_BY_SPEAKER_CONFERENCE = endpoints.ResourceContainer(
    websafeSpeakerKey=messages.StringField(1),
    websafeConferenceKey=messages.StringField(2),
)
SESSION_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeSessionKey=messages.StringField(1),
)
REMOVE_SESSION_POST_REQUEST = endpoints.ResourceContainer(
    websafeSessionKey=messages.StringField(1),
    removeConference=messages.BooleanField(2)
)
GET_SPEAKERS_BY_NAME = endpoints.ResourceContainer(
    displayName=messages.StringField(1),
)
SESSION_POST_REQUEST = endpoints.ResourceContainer(
    ConferenceSessionForm,
    websafeConferenceKey=messages.StringField(1),
)
CONF_SESSION_TYPE_REQUEST = endpoints.ResourceContainer(
    websafeConferenceKey=messages.StringField(1),
    typeOfSession=messages.StringField(2, repeated=True)
)
QUERY_PROBLEM = endpoints.ResourceContainer(
    afterTime=messages.IntegerField(1),
    exclude=messages.StringField(2, repeated=True)
)
QUERY_PROBLEM2 = endpoints.ResourceContainer(
    after_time=messages.StringField(1),
    before_time=messages.StringField(2),
    exclude_types=messages.StringField(3, repeated=True),
    include_types=messages.StringField(4, repeated=True),
    search_highlights=messages.StringField(5),
    search_general=messages.StringField(6)
)
# - - - - - - - - - - - - end added_by @Robert_Avram - - - - - - - - - - - - - - - - - -