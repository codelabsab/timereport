#!/usr/bin/env python
import os
import re
import datetime
import json

from pprint import pprint
from dateutil.parser import parse
from flask import Flask, request, make_response, Response, jsonify
from slackeventsapi import SlackEventAdapter
from slackclient import SlackClient
from dotenv import load_dotenv, find_dotenv
from flask_pymongo import PyMongo

# load .env file with secrets
load_dotenv(find_dotenv())

# Your app's Slack bot user token
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_VERIFICATION_TOKEN = os.environ["SLACK_VERIFICATION_TOKEN"]

# Slack client for Web API requests
slack_client = SlackClient(SLACK_BOT_TOKEN)

# Flask webserver for incoming traffic from Slack
app = Flask(__name__)
app.config['DEBUG'] = True

# MONGO DB VALUES
app.config['MONGO_HOST'] = os.environ["MONGO_HOST"]
app.config['MONGO_PORT'] = os.environ["MONGO_PORT"]
app.config['MONGO_USERNAME'] = os.environ["MONGO_USERNAME"]
app.config['MONGO_PASSWORD'] = os.environ["MONGO_PASSWORD"]
app.config['MONGO_DBNAME'] = os.environ["MONGO_DBNAME"]
mongo = PyMongo(app)

# Helper for validating a date string
def validateDate(date):
    try:
        datetime.datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return ValueError("Incorrect date format, should be YYYY-MM-DD")

# Helper for verifying that requests came from Slack
def verify_slack_token(request_token):
    if SLACK_VERIFICATION_TOKEN != request_token:
        print("Error: invalid verification token!")
        print("Received {} but was expecting {}".format(request_token, SLACK_VERIFICATION_TOKEN))
        return make_response("Request contains invalid Slack verification token", 403)

def postEphemeral(attachment, channel_id, user_id):
    slack_client.api_call(
            "chat.postEphemeral",
            channel=channel_id,
            user=user_id,
            attachments=attachment
    )

def postMessage(channel_id, user_id, type_id, date, hours, attachment=None):
    if attachment is None:
        attachment=[
        {
            "fields": [
                {
                    "title": "Type",
                    "value": "{}".format(type_id)
                },
                {
                    "title": "Date",
                    "value": "{}".format(date)
                },
                {
                    "title": "Hours",
                    "value": "{}".format(hours)
                }
           ],
        "footer": "Code Labs timereport",
        "footer_icon": "https://codelabs.se/favicon.ico",
       "fallback": "Submit these values?",
       "title": "Submit these values?",
       "callback_id": "submit",
       "color": "#3AA3E3",
       "attachment_type": "default",
       "actions": [
                {
                    "name": "submit",
                    "text": "submit",
                    "type": "button",
                    "style": "primary",
                    "value": "submit_yes"
                },
                {
                    "name": "no",
                    "text": "No",
                    "type": "button",
                    "style": "danger",
                    "value": "submit_no"
                }
            ]
       }
       ]

    slack_client.api_call(
            "chat.postMessage",
            channel=channel_id,
            user=user_id,
            attachments=attachment
    )

def chatUpdate(channel_id, message_ts, text, user_id):
    slack_client.api_call(
              "chat.update",
              channel=channel_id,
              ts=message_ts,
              text="<@{}> {}".format(user_id, text),
              attachments=[] # empty `attachments` to clear the existing massage attachments
    )
def dateToday():
    # create today's date stamp
    today = datetime.datetime.today()
    year = today.year
    month = today.month
    day = today.day
    date = "{:4d}-{:02d}-{:02d}".format(year, month, day)
    validateDate(date)
    return date

def mongoSubmit(user_id, user_name, input_type_id, input_hours, input_date, input_date_end=None):
    # strip date into smaller chunks
    date_year = input_date.split('-')[0]
    date_month = input_date.split('-')[1]
    date_day = input_date.split('-')[2]

    # set to start date if end is not given
    if input_date_end is None:
        date_end = input_date
        date_month_end = date_month
        date_day_end = date_day

    return mongo.db.users.insert(
    {
        "user_id": user_id,
        "user_name": user_name,
        "type_id": input_type_id,
        "hours": input_hours,
        "date": {
            "date": input_date,
            "date_end": date_end,
            "date_year": date_year,
            "date_month": date_month,
            "date_month_end": date_month_end,
            "date_day": date_day,
            "date_day_end": date_day_end
        }
    })


@app.route("/fetch", methods=["POST"])
def fetch():
    # save the token
    slack_token = request.form.get("token")
    # Verify that the request came from Slack
    verify_slack_token(slack_token)
    # assign the request values
    channel_id = request.form.get('channel_id')
    user_id = request.form.get('user_id')
    user_name = request.form.get('user_name')
    text = request.form.get('text')
    command = request.form.get('command')
    if text:
        text_list = text.split(' ')

    if "help" in text_list[0] or len(text) == 0:
        text_list = []
        help_menu=[
            {
            "color": "#3A6DE1",
            "pretext": "Help menu",
            "fields": [
                {
                    "title": "{} <YYYY-MM|optional> <user|optional>".format(command),
                    "value": "fetch from database by providing year month and username or nothing for all"

                },
		{
                    "title": "{} <YYYY-MM|optional> <all|optional>".format(command),
                    "value": "fetch from database all users for a specific month"
                },
                {
                    "title": "Argument: <YYYY-MM>",
                    "value": "2018-03 or empty for todays month as default value"
                },
                {
                    "title": "Argument: <user|optional>",
                    "value": "<user> will fetch data for specific user from database"
                }
            ],
            "footer": "Code Labs timereport",
            "footer_icon": "https://codelabs.se/favicon.ico",
            }
          ]

        postEphemeral(help_menu, channel_id, user_id)

    # probably <YYYY-MM> <user> provided
    if len(text_list) == 2:
        year = text_list[0].split('-')[0]
        month = text_list[0].split('-')[1]
        full_date = "{}-{}".format(year, month)
        user = text_list[1] # save user second argument
        if user == "all":
            mongo_query = { "date.date_month": month, "date.date_year": year }
        else:
            mongo_query = { "date.date_month": month, "date.date_year": year, "user_name": user }
     # are we providing <YYYY-MM> or <user>
    elif len(text_list) == 1:
        date = dateToday()
        year = date.split('-')[0]
        month = date.split('-')[1]
        # date first argument
        if re.match('^[0-9][0-9][0-9][0-9]-[0-9][0-9]$', text_list[0]):
            year = text_list[0].split('-')[0]
            month = text_list[0].split('-')[1]
            full_date = "{}-{}".format(year, month)
        # username first argument
        elif text_list[0] == user_name:
            # fetch todays month entries
            mongo_query = { "date.date_month": month, "date.date_year": year, "user_name": user_name }
        # if argument is date format only fetch for this month
        else:
            mongo_query = { "date.date_month": month, "date.date_year": year, "user_name": text_list[0] }
    else:
        return make_response("", 200)
        date = dateToday()
        year = date.split('-')[0]
        month = date.split('-')[1]
   #     mongo_query = { "date.date_month": month, "date.date_year": year }
   #     full_date = "{}-{}".format(year, month)


    full_date = "{}-{}".format(year, month)
    try:
        mongo_query
    except NameError:
        mongo_query = { "date.date_month": month, "date.date_year": year }
    mongo_filter = { "user_name": 1, "date.date": 1, "type_id": 1, "hours": 1, "_id": 0 }
    users = mongo.db.users.find(mongo_query , mongo_filter)
    if users.count() >= 1:
        for u in users:
            date = u['date']['date']
            hours = u['hours']
            type_id = u['type_id']
            user_name = u['user_name']
            text = "*****Values for {} ******\nUser: {}\nDate: {}\nType: {}\nHours: {}".format(full_date,user_name,date,type_id,hours)
            print("*****Values for {} ******\nUser: {}\nDate: {}\nType: {}\nHours: {}".format(full_date,user_name,date,type_id,hours))
            slack_client.api_call(
                "chat.postMessage",
                channel=channel_id,
                user=user_id,
                text=text
            )
    else:
        return make_response("Nothing found in database for {} {}".format(command, text))

    return make_response("", 200)

@app.route("/", methods=["POST"])
def timereport():
    # save the token
    slack_token = request.form.get("token")
    # Verify that the request came from Slack
    verify_slack_token(slack_token)

    # assign the request values
    channel_id = request.form.get('channel_id')
    user_id = request.form.get('user_id')
    text = request.form.get('text')
    command = request.form.get('command')
    response_url = request.form.get('response_url')
    trigger = request.form.get('trigger_id')
    deviation_type = ["vab", "betald_sjukdag", "obetald_sjukdag", "ledig", "semester", "foraldrar_ledigt", "end" ]

    # split text arguments into list
    text_list = text.split(' ')

    # the dialog to display if nothing or help was the input
    if "help" in text_list[0] or len(text) == 0:
        help_menu=[
            {
            "color": "#3A6DE1",
            "pretext": "Help menu",
            "fields": [
                {
                    "title": "{} <type> <today> <hours|optional>".format(command),
                    "value": "create a single day deviation of <type> at <today>"

                },
		{
                    "title": "{} <type> <YYYY-MM-DD> <hours|optional>".format(command),
                    "value": "create a single day deviation of <type> at <date> <hours|optional>"
                },
                {
                    "title": "Argument: <type>",
                    "value": "{}".format(' '.join(deviation_type).replace(' ', ' | '))
                },
                {
                    "title": "Argument: <today|<YYYY-MM-DD>",
                    "value": "<today> will set todays date or use <YYYY-MM-DD> format to specify date."
                },
                {
                    "title": "Argument: <hours|optional>",
                    "value": "<hours> will set number of hours.\nThis is optional and will default to 8 hours if not specified."
                }
            ],
            "footer": "Code Labs timereport",
            "footer_icon": "https://codelabs.se/favicon.ico",
            }
          ]

        postEphemeral(help_menu, channel_id, user_id)
    # are we providing at least 2 arguments but not more than 3
    elif len(text_list) >=2 or len(text_list) <=3:

        # is first argument the type_id we have in deviation_type
        if text_list[0] in deviation_type:
            type_id = text_list[0]
        else:
            return make_response("wrong <type> argument: {}".format(text_list[0]), 200)

        if "today" in text_list[1]:
            # set date to today
            date = dateToday()
           # validate second parameter so it is a correct formatted date (return None if successful)
        elif validateDate(''.join(text_list[1])) is None:
            # set date variable
            date = ''.join(text_list[1])
        else:
            return make_response("wrong <date> provided: {}".format(text_list[1]), 200)

        # get hours from last argument proided
        if re.match('^[0-8]$', ''.join(text_list[-1:])):
            hours = ''.join(text_list[-1:])
        elif ''.join(text_list[-1:]) == "today" or ''.join(text_list[-1:]) == date:
            # default to 8 hours if last parameter is the date parameter
            hours = '8'
        else:
            return make_response("wrong <hours> provided: {} instead of [1-8]".format(''.join(text_list[-1:])))

        # if we get here then everything should be fine and we have collected all values
        postMessage(channel_id, user_id, type_id, date, hours)
    else:
        return make_response("wrong number of arguments provided: {}. <type> <date|today> <hours|optional>".format(len(text_list)), 200)



    # return ok here
    return make_response("", 200)

@app.route("/slack/message_actions", methods=["POST"])
def message_actions():

    # Parse the request payload
    form_json = json.loads(request.form["payload"])

    # Verify that the request came from Slack
    verify_slack_token(form_json["token"])

    # Check to see what the user's selection was and update the message accordingly
    # save values
    channel_id = form_json["channel"]["id"]
    message_ts = form_json["message_ts"]
    user_id = form_json["user"]["id"]
    user_name = form_json['user']['name']

    if form_json["type"] == "interactive_message":
        # save values
        selection = form_json["actions"][0]["value"]
        input_type_id = json.dumps(form_json["original_message"]["attachments"][0]["fields"][0]["value"]).strip('"')
        input_hours = json.dumps(form_json["original_message"]["attachments"][0]["fields"][2]["value"]).strip('"')
        input_date = json.dumps(form_json["original_message"]["attachments"][0]["fields"][1]["value"]).strip('"')
        date_month = input_date.split('-')[1]

        if selection == "submit_yes":
            # do DB stuff here
            print("doing database stuff")
            print("user_id: {}\n user_name: {}\n, input_type_id: {}\n, input_hours: {}\n, input_date: {}\n".format(repr(user_id), repr(user_name), repr(input_type_id), repr(input_hours), repr(input_date)))
            mongoSubmit(user_id, user_name, input_type_id, input_hours, input_date)
            users = mongo.db.users.find({ "date.date_year": "2018", "date.date_month": "03" })
            for u in users:
                pprint(u)

            chatUpdate(channel_id, message_ts, "submitted timereports successfully :thumbsup:", user_id)

            # Send an HTTP 200 response with empty body so Slack ktodays we're done here
            return make_response("", 200)


        else:
            return make_response("canceling...", 200)

    else:
        print("regular message stuff")


    # Send an HTTP 200 response with empty body so Slack ktodays we're done here
    return make_response("", 200)

# Start the Flask server
if __name__ == "__main__":
   app.run(host="0.0.0.0", port=os.environ["LISTEN_PORT"])
