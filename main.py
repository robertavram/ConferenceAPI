"""
main.py -- Udacity conference server-side Python App Engine
    HTTP controller handlers for memcache & task queue access

    originally created by wesc on 2014 may 24 by wesc+api@google.com (Wesley Chun)
    
    updated by @Robert_Avram on 2015 June 6

"""

__author__ = 'Robert Avram'

import webapp2
from google.appengine.api import app_identity
from google.appengine.api import mail
from conference import ConferenceApi


class SetAnnouncementHandler(webapp2.RequestHandler):

    def get(self):
        """Set Announcement in Memcache."""
        ConferenceApi._cacheAnnouncement()
        self.response.set_status(204)


class AddFeaturedSpeaker(webapp2.RequestHandler):

    def post(self):
        """Set Featured Speaker"""
        ConferenceApi._setFeaturedSpeaker(self.request.get("speaker_name"),
                                          self.request.get_all("sess_keys"),
                                          self.request.get(
                                              "current_sess_name"),
                                          self.request.get("conf"),
                                          self.request.get("conf_loc"))


class SendConfirmationEmailHandler(webapp2.RequestHandler):

    def post(self):
        """Send email confirming Conference creation."""
        mail.send_mail(
            'noreply@%s.appspotmail.com' % (
                app_identity.get_application_id()),     # from
            self.request.get('email'),                  # to
            'You created a new Conference!',            # subj
            'Hi, you have created a following '         # body
            'conference:\r\n\r\n%s' % self.request.get(
                'conferenceInfo')
        )


app = webapp2.WSGIApplication([
    ('/crons/set_announcement', SetAnnouncementHandler),
    ('/tasks/send_confirmation_email', SendConfirmationEmailHandler),
    ('/tasks/add_featured_speaker', AddFeaturedSpeaker),
], debug=True)
