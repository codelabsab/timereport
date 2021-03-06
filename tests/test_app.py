import random

import pytest
from tests.utils import call_from_slack, get_raw_block_text, respond_interactively


def test_help_command(chalice_app):
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command="help",
        user_id=f"{random.randint(0, 10000)}",
        user_name="mattias",
    )

    assert r["response"]["statusCode"] == 200
    assert "Supported actions" in r["slack_message"][1]["json"]["text"]
    assert "unsupported" not in r["slack_message"][1]["json"]["text"]


def test_help_specific_command(chalice_app):
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command="help add",
        user_id=f"{random.randint(0, 10000)}",
        user_name="mattias",
    )

    assert r["response"]["statusCode"] == 200
    assert "/timereport add" in r["slack_message"][1]["json"]["text"]


def test_help_unknown_command(chalice_app):
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command="help foo",
        user_id=f"{random.randint(0, 10000)}",
        user_name="mattias",
    )

    assert r["response"]["statusCode"] == 200
    assert "Supported actions" in r["slack_message"][1]["json"]["text"]


@pytest.mark.integration
def test_empty_list(chalice_app):
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command="list today",
        user_id=f"{random.randint(0, 10000)}",
        user_name="mattias",
    )

    assert r["response"]["statusCode"] == 200
    assert "nothing to list" in r["slack_message"][1]["json"]["text"]


@pytest.mark.integration
@pytest.mark.parametrize(
    "date,hours",
    [
        ("today", "8"),
        ("2020-01-01", "8"),
        ("today", "6.5"),
        ("2020-01-01:2020-01-02", "8"),
    ],
)
def test_add_command_accepted(chalice_app, date, hours):
    user_id = f"{random.randint(0, 10000)}"
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command=f"add vab {date} {hours}",
        user_id=user_id,
        user_name="mattias",
    )

    assert r["response"]["statusCode"] == 200
    assert "From timereport" in r["slack_message"][1]["json"]["text"]
    attachments = r["slack_message"][1]["json"]["attachments"]
    assert attachments is not None
    attachment = attachments[0]
    assert attachment["actions"]
    assert "Submit" in attachment["title"]

    ri = respond_interactively(
        chalice_app=chalice_app,
        attachments=attachments,
        user_id=user_id,
        callback_id="add",
    )
    assert ri["response"]["statusCode"] == 200
    assert "success" in ri["slack_message"][1]["json"]["text"]

    rl = call_from_slack(
        chalice_app=chalice_app,
        full_command=f"list {date}",
        user_id=user_id,
        user_name="mattias",
    )
    assert rl["response"]["statusCode"] == 200
    assert "nothing to list" not in rl["slack_message"][1]["json"]["text"]
    assert "Reason: *vab*" in get_raw_block_text(slack_message=rl["slack_message"])
    assert f"Hours: *{hours}" in get_raw_block_text(slack_message=rl["slack_message"])

    if ":" in date:
        return  # Delete doesn't support ranges

    # Delete report
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command=f"delete {date}",
        user_id=user_id,
        user_name="mattias",
    )

    assert r["response"]["statusCode"] == 200
    assert "From timereport" in r["slack_message"][1]["json"]["text"]

    attachments = r["slack_message"][1]["json"]["attachments"]
    assert attachments is not None
    attachment = attachments[0]
    assert attachment["actions"]
    assert "Delete" in attachment["title"]

    ri = respond_interactively(
        chalice_app=chalice_app,
        attachments=attachments,
        user_id=user_id,
        callback_id="delete",
    )
    assert ri["response"]["statusCode"] == 200
    assert "Deleted 1" in ri["slack_message"][1]["json"]["text"]

    rl = call_from_slack(
        chalice_app=chalice_app,
        full_command=f"list {date}",
        user_id=user_id,
        user_name="mattias",
    )
    assert rl["response"]["statusCode"] == 200
    assert "nothing to list" in rl["slack_message"][1]["json"]["text"]


@pytest.mark.integration
def test_delete_non_existing(chalice_app):
    user_id = f"{random.randint(0, 10000)}"
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command=f"delete today",
        user_id=user_id,
        user_name="mattias",
    )

    assert r["response"]["statusCode"] == 200
    assert "no events found" in r["slack_message"][1]["json"]["text"]


@pytest.mark.integration
def test_list_current_period(chalice_app):
    user_id = f"{random.randint(0, 10000)}"
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command="add vab today 8",
        user_id=user_id,
        user_name="mattias",
    )

    assert r["response"]["statusCode"] == 200
    attachments = r["slack_message"][1]["json"]["attachments"]

    ri = respond_interactively(
        chalice_app=chalice_app,
        attachments=attachments,
        user_id=user_id,
        callback_id="add",
    )
    assert ri["response"]["statusCode"] == 200
    assert "success" in ri["slack_message"][1]["json"]["text"]

    rl = call_from_slack(
        chalice_app=chalice_app,
        full_command=f"list",
        user_id=user_id,
        user_name="mattias",
    )
    assert rl["response"]["statusCode"] == 200
    assert "nothing to list" not in rl["slack_message"][1]["json"]["text"]
    raw_block_text = get_raw_block_text(slack_message=rl["slack_message"])
    assert "Reason: *vab*" in raw_block_text

    assert "vab: 8.0h" in raw_block_text


@pytest.mark.integration
def test_list_with_total_hours(chalice_app):
    # 3 days vab, public holiday, weekday, weekend
    user_id = f"{random.randint(0, 10000)}"
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command="add vab 2020-05-21:2020-05-23 8",
        user_id=user_id,
        user_name="mattias",
    )

    assert r["response"]["statusCode"] == 200
    attachments = r["slack_message"][1]["json"]["attachments"]

    ri = respond_interactively(
        chalice_app=chalice_app,
        attachments=attachments,
        user_id=user_id,
        callback_id="add",
    )
    assert ri["response"]["statusCode"] == 200
    assert "success" in ri["slack_message"][1]["json"]["text"]

    rl = call_from_slack(
        chalice_app=chalice_app,
        full_command=f"list 2020-05",
        user_id=user_id,
        user_name="mattias",
    )
    assert rl["response"]["statusCode"] == 200
    assert "nothing to list" not in rl["slack_message"][1]["json"]["text"]
    raw_block_text = get_raw_block_text(slack_message=rl["slack_message"])
    assert "Reason: *vab*" in raw_block_text

    # 152 hours total in month, 8 vab on weekdays and 16 vab on weekends/holidays (not counted)
    assert "144.0 / 152 (-8.0)" in raw_block_text
    assert "vab: 8.0h" in raw_block_text


@pytest.mark.integration
@pytest.mark.parametrize("date", ["today", "2020-01-01"])
def test_add_command_accepted_and_edited(chalice_app, date):
    user_id = f"{random.randint(0, 10000)}"
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command=f"add vab {date} 8",
        user_id=user_id,
        user_name="mattias",
    )

    assert r["response"]["statusCode"] == 200
    assert r["slack_message"][1]["json"]["text"] == "From timereport"
    attachments = r["slack_message"][1]["json"]["attachments"]
    assert attachments is not None
    attachment = attachments[0]
    assert attachment["actions"]
    assert "Submit" in attachment["title"]

    ri = respond_interactively(
        chalice_app=chalice_app,
        attachments=attachments,
        user_id=user_id,
        callback_id="add",
    )
    assert ri["response"]["statusCode"] == 200
    assert ri["slack_message"][1]["json"]["text"] == "Added successfully"

    rl = call_from_slack(
        chalice_app=chalice_app,
        full_command=f"list {date}",
        user_id=user_id,
        user_name="mattias",
    )
    assert rl["response"]["statusCode"] == 200
    assert "nothing to list" not in rl["slack_message"][1]["json"]["text"]
    assert "Reason: *vab*" in get_raw_block_text(slack_message=rl["slack_message"])

    # Change to sjuk
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command=f"edit sjuk {date} 8",
        user_id=user_id,
        user_name="mattias",
    )

    assert r["response"]["statusCode"] == 200
    assert r["slack_message"][1]["json"]["text"] == "From timereport"

    attachments = r["slack_message"][1]["json"]["attachments"]
    assert attachments is not None
    attachment = attachments[0]
    assert attachment["actions"]
    assert "Submit these values" in attachment["title"]

    ri = respond_interactively(
        chalice_app=chalice_app,
        attachments=attachments,
        user_id=user_id,
        callback_id="add",
    )
    assert ri["response"]["statusCode"] == 200
    assert "Added successfully" in ri["slack_message"][1]["json"]["text"]

    rl = call_from_slack(
        chalice_app=chalice_app,
        full_command=f"list {date}",
        user_id=user_id,
        user_name="mattias",
    )
    assert rl["response"]["statusCode"] == 200
    assert "nothing to list" not in rl["slack_message"][1]["json"]["text"]
    assert "Reason: *sjuk*" in get_raw_block_text(slack_message=rl["slack_message"])


@pytest.mark.integration
def test_add_command_rejected(chalice_app):
    user_id = f"{random.randint(0, 10000)}"
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command="add vab today 8",
        user_id=user_id,
        user_name="mattias",
    )

    assert r["response"]["statusCode"] == 200
    assert "From timereport" in r["slack_message"][1]["json"]["text"]
    attachments = r["slack_message"][1]["json"]["attachments"]
    assert attachments is not None
    attachment = attachments[0]
    assert attachment["actions"]
    assert "Submit" in attachment["title"]

    ri = respond_interactively(
        chalice_app=chalice_app,
        attachments=attachments,
        user_id=user_id,
        action="submit_no",
        callback_id="add",
    )
    assert ri["response"]["statusCode"] == 200
    assert "canceled" in ri["slack_message"][1]["json"]["text"]


@pytest.mark.integration
def test_lock_month_and_list(chalice_app):
    user_id = f"{random.randint(0, 10000)}"
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command="lock 2020-07",
        user_id=user_id,
        user_name="mattias",
    )
    assert r["response"]["statusCode"] == 200
    assert "Lock successful" in r["slack_message"][1]["json"]["text"]

    r = call_from_slack(
        chalice_app=chalice_app,
        full_command="lock 2019-07",
        user_id=user_id,
        user_name="mattias",
    )
    assert r["response"]["statusCode"] == 200
    assert "Lock successful" in r["slack_message"][1]["json"]["text"]

    r = call_from_slack(
        chalice_app=chalice_app,
        full_command="lock list 2020",
        user_id=user_id,
        user_name="mattias",
    )
    assert r["response"]["statusCode"] == 200

    raw_block_text = get_raw_block_text(slack_message=r["slack_message"])
    assert "Locks found for" in raw_block_text
    assert "2020-07" in raw_block_text
    assert "2019-07" not in raw_block_text


@pytest.mark.integration
def test_lock_month_add(chalice_app):
    user_id = f"{random.randint(0, 10000)}"
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command="lock 2020-07",
        user_id=user_id,
        user_name="mattias",
    )
    assert r["response"]["statusCode"] == 200
    assert "Lock successful" in r["slack_message"][1]["json"]["text"]

    # Add in locked period
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command="lock list 2020",
        user_id=user_id,
        user_name="mattias",
    )
    assert r["response"]["statusCode"] == 200

    raw_block_text = get_raw_block_text(slack_message=r["slack_message"])
    assert "Locks found for" in raw_block_text
    assert "2020-07" in raw_block_text

    # Add in non locked period
    r = call_from_slack(
        chalice_app=chalice_app,
        full_command=f"add vab 2020-08-03 8",
        user_id=user_id,
        user_name="mattias",
    )

    assert r["response"]["statusCode"] == 200
    assert r["slack_message"][1]["json"]["text"] != "are locked"
