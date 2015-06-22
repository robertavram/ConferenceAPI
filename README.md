App Engine application for the Udacity training course.

## Products
- [App Engine][1]

## Language
- [Python][2]

## APIs
- [Google Cloud Endpoints][3]
- [Search][7]

## Setup Instructions
1. Update the value of `your-application-name` in `app.yaml` to the app ID you
   have registered in the App Engine admin console and would like to use to host
   your instance of this sample.
1. Update the values at the top of `settings.py` to
   reflect the respective client IDs you have registered in the
   [Developer Console][4].
1. Update the value of CLIENT_ID in `static/js/app.js` to the Web client ID
1. (Optional) Mark the configuration files as unchanged as follows:
   `$ git update-index --assume-unchanged app.yaml settings.py static/js/app.js`
1. Run the app with the devserver using `dev_appserver.py DIR`, and ensure it's running by visiting your local server's address (by default [localhost:8080][5].)
1. (Optional) Generate your client library(ies) with [the endpoints tool][6].
1. Deploy your application.


# **Task 1: Add Sessions to a Conference**

## Design Choices Explanation

*Explain in a couple of paragraphs your design choices for session and speaker implementation.*

1. `ConferenceSpeaker` is stored as its own model, independent of any user or conference. I chose to use it in this manner because speakers could present at different conferences, could eventually have ratings, previous conferences, future conferences etc; basically their own more comprehensive profiles. For now only `displayName` is in their model.

2. `ConferenceSession` is an entity model that inherits as a parent the conference for which it is created. I chose the parent inheritance because it becomes easier to query. The other option would have been to have a sessions field repeated `keyProperty` on `Conference`, but that would have added more friction for removing sessions. Would have had the benefit of not having to query the db in order to retrieve all the sessions in a conference, but the downfall of storing an extra field of data. Either way :)

# **Task 3: Indexes and Queries**

## Two additional queries

*Think about other types of queries that would be useful for this application. Describe the purpose of 2 new queries and write the code that would perform them.*

There are many queries that should potentially be added, I’ve implemented a different way of querying sessions when solving the query related problem (see below). 

Qry 1: Get a speaker by name: Let’s say that a conference organizer registered a speaker for an earlier conference, now the organizer wants to use this speaker for a session, somehow she needs to get the speaker key and she only knows the name. Querying all speakers by name seems important.

* `conference.getSpeakerByName`

Qry 2: Given a speaker and a conference return all sessions that have that speaker. Let’s say that a fanboy wants to attend all sessions from a certain speaker in a specific conference.

* `conference.getSessionsFromSpeakerAndConference`

## Query Related Problem

*Let’s say that you don't like workshops and you don't like sessions after 7 pm. How would you handle a query for all non-workshop sessions before 7 pm? What is the problem for implementing this query? What ways to solve it did you think of?*

Answer:

The query introduces the problem of two inequality filters. Since one inequality filter is searching for `startTime > 19:00` and the seccond is `type != workshops` which is executed with an `OR` statement like: `type < "workshop" OR type > “workshop”`.

There are a few ways to solve this problem:

1. Have a list of allowed `ConferenceSession` types like `allowed_types = [‘workshop’, ‘keynote’, ‘other’]` and query based on membership like: `ConferenceSession.type.IN(allowed_types.remove(‘workshop’))`, this way the query becomes an equality query with OR like: `ConferenceSession.type == ‘keynote’ OR ConferenceSession.type == ‘other’`:

    1. Drawbacks: If the list of allowed types is very large, the query becomes slower since it checks for a match in a large list.

    2. Advantages: This will work well if we decide that `ConferenceSession.type` can be a repeated property (in case a session is both a workshop and something else), this way we can match multiple types.

2. Add a property `startTimeSlot` to `ConferenceSession` model which is computed based on the start time (eg: conference starts at 19:05 startTimeSlot is "19"(as in hour 19)), then like in the previous point make a list of allowed timeSlots and apply a membership filter removing the timeSlots that are not wanted (in this case removing `[“19”,”20”,”21”,”22”,”23”]`). the filter will then look like: `ConferenceSession.startTimeSlot.IN(allowedTimeSlots)` - where `allowedTimeSlots` is a list that includes all the possible timeslots for sessions within that conference on that day minus the unwanted times.

    1. Drawbacks:

        1. it limits the specificity  that a user is allowed to query by (eg if a user likes sessions that start at 7 but doesn’t like sessions after 7:30 his choices are limited to querying sessions either before 7 or before 8 and not before 7:30) - we could reduce the timeSlots to fit half hour blocks but that just opens up another problem with query speed since we’d be trying to match against a larger list.

        2.  adding a computed property after the application is running and there is existing data in the DB it requires extra legwork to update the model’s schema. The entities that don’t have the property computed need to be re-put.

    2. Advantages: 

        3. if done correctly we won’t need to worry about updating it in the future since most likely the 24 hour time measuring system is going to hold up for years to come :), unlike the previous example where we have to worry about loss of efficiency every time we add a new type of session.

*I consider that out of the two, the first one would be better suited in this particular case because realistically there are only a few types of sessions and the field should be restricted to certain values anyway. Also allowing the inequality filter to be on the `startTime` would enable us to order by time first which in my opinion makes more sense than ordering by session type first. In this project I implemented the `startTimeSlot` purely because I thought it would be slightly more challenging :). (look for `queryproblem` method in the conference api)*

3. While both those solutions can be good in many cases, I believe the best solution in this case (the conference app), in terms of querying for sessions, is the Search API available in google app engine. This since one might want to run much more complex queries in different ways. 

   * *Example: I want to know all sessions that talk about App Engine or Udacity (this would be in the highlights) that are not workshops and start before 11am or after 6pm, that are in programming conferences (this would be in the description of the conference) around San Francisco.*

 	Since queries like this will take significant DB re-architecting, and a tremendous amount of time for figuring out all the potential indexes, creating a document for each session with the Search API seems to me like the best solution in this case. Even though search API queries are more expensive to run than NDB queries, I feel like the ability to return more relevant results quicker and reducing the development time when it comes to full text search within the DB is well worth it. :)

   *I have implemented this type of querying mechanism in `queryproblem2` in the conference api.*

### Version
0.0.1


License
----

Apache License
Version 2.0, January 2004


**Free Software**
   
   
[1]: https://developers.google.com/appengine
[2]: http://python.org
[3]: https://developers.google.com/appengine/docs/python/endpoints/
[4]: https://console.developers.google.com/
[5]: https://localhost:8080/
[6]: https://developers.google.com/appengine/docs/python/endpoints/endpoints_tool
[7]: https://cloud.google.com/appengine/docs/python/search/
