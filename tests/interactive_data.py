payload = {
    'type': 'interactive_message',
    'actions': [
        {
            'name': 'submit',
            'type': 'button',
            'value': 'submit_yes'
        }
    ],
    'callback_id': 'add',
    'team': {
        'id': 'T2FG58LDV',
        'domain': 'codelabsab'
    },
    'channel': {
        'id': 'D875JCC4D',
        'name': 'directmessage'
    },
    'user': {
        'id': 'U86BEEK5W',
        'name': 'par.berge'
    },
    'action_ts': '1569700502.301822',
    'message_ts': '1569700499.000200',
    'attachment_id': '1',
    'token': 'ZfnrFKdHTDIy3f60ahIw4HO4',
    'is_app_unfurl': False,
    'original_message': {
        'type': 'message',
        'subtype': 'bot_message',
        'text': 'From timereport',
        'ts': '1569700499.000200',
        'username': 'timereport-dev',
        'bot_id': 'BEB7VGM28',
        'attachments': [
            {
                'callback_id': 'add',
                'fallback': 'Submit these values to database?',
                'title': 'Submit these values to database?',
                'footer': 'Code Labs timereport',
                'id': 1,
                'footer_icon': 'https://codelabs.se/favicon.ico',
                'color': '3AA3E3',
                'fields': [
                    {
                        'title': 'User',
                        'value': 'par.berge',
                        'short': False
                    }, {
                        'title': 'Type',
                        'value': 'vab',
                        'short': False
                    }, {
                        'title': 'Date start',
                        'value': '2019-09-28',
                        'short': False
                    }, {
                        'title': 'Date end',
                        'value': '2019-09-28',
                        'short': False
                    }, {
                        'title': 'Hours',
                        'value': '8',
                        'short': False
                    }
                ],
                'actions': [
                    {
                        'id': '1',
                        'name': 'submit',
                        'text': 'submit',
                        'type': 'button',
                        'value': 'submit_yes',
                        'style': 'primary'
                    }, {
                        'id': '2',
                        'name': 'no',
                        'text': 'No',
                        'type': 'button',
                        'value': 'submit_no',
                        'style': 'danger'
                    }]
            }
        ]
    },
    'response_url': 'https://hooks.slack.com/actions/T2FG58LDV/770496643713/1wfaV4Lwz5wmXYzgVHaZNZe3',
    'trigger_id': '770496643745.83549292471.2b63a8d8adc98bfe84fffe4a0faccb95'
}