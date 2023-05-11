# Base libraries
# Langchain and OpenAI
from flask import Flask

from langchain.agents import AgentExecutor
from langchain.chat_models import ChatOpenAI
from langchain.llms.openai import OpenAI
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import create_sql_agent
import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
# Data libraries
import pandas as pd
import numpy as np
import sqlalchemy as sqla

# User libraries

load_dotenv()

appFlask = Flask(__name__)

slackBotToken = os.getenv("SLACK_BOT_TOKEN")
slackAppToken = os.getenv("SLACK_APP_TOKEN")

app = App(token=slackBotToken)

conn_string = os.getenv("DB_URL")
engine = sqla.create_engine(conn_string)


# Langchain objects
# -----------------

# Database
db = SQLDatabase.from_uri(conn_string)

# Model
llm = ChatOpenAI(model_name='gpt-3.5-turbo')

# Agent
toolkit = SQLDatabaseToolkit(db=db, llm=llm, verbose=True)
agent_executor = create_sql_agent(
    llm=OpenAI(temperature=0),
    toolkit=toolkit,
)

cantData = ""


@app.message("hello")
def message_hello(client, message, say):
    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Hello, that are my principal options :smile:. *Please, be patient, i need time to think to give you a good answer*"
                }
            },
            {
                "type": "actions",
                "block_id": "actionblock789",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Number"
                                    },
                                    "style": "primary",
                                    "value": "click_me_1",
                                    "style": "primary",
                                    "action_id": "button_one_data"
                                },
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Table"
                                    },
                                    "style": "primary",
                                    "value": "click_me_1",
                                    "style": "primary",
                                    "action_id": "button_multiple"
                                },
                            ]
            }
        ],
        text=f"Hey there <@{message['user']}>!"
    )


@app.action("button_one_data")
def action_button_click(body, ack, say):
    ack()
    global cantData
    cantData = "0"
    say("Perfect, i will remember that selection")
    say("Now you can ask me something about Kiwi Financial INC")


@app.action("button_multiple")
def action_button_click(body, ack, say):
    ack()
    global cantData
    cantData = "1"
    say("Perfect, i will remember that selection")
    say("Now you can ask me something about Kiwi Financial INC")


# @app.event("app_mention")
# def event_test(ack, body, say, logger):
#     ack()
#     logger.info(body)
#     say(f'Your question is: {body["event"]["text"]}')
#     say("Wait a moment, i'm thinking...")
#     gpt_response = agent_executor.run(body["event"]["text"])
#     # <@{body["event"]["user_id"]}>,
#     say(f'your answer is: {gpt_response}')


# @app.command("/train_me")
# def repeat_text(ack, body, respond):
#     ack()
#     respond("Wait a moment, i'm thinking...")
#     gpt_response = agent_executor.run(f"{body['text']}")
#     respond(f"<@{body['user_id']}>, your answer is: {gpt_response}")


@app.event("message")
def handle_message_events(ack, client, body, say, logger):
    ack()
    logger.info(body)

    event = body["event"]
    thread_ts = event.get("thread_ts", None) or event["ts"]

    global cantData

    if cantData == "":
        say("To intiate chat with AthenaSQL please type 'hello'")
        return

    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f'Your question is: *{body["event"]["text"]}*'
                }
            }],
        thread_ts=thread_ts,
        text=f"Hey there!"
    )

    # responseUploadImg = app.client.files_upload(
    #       filename='test',
    #       filetype="png",
    #       title='Sample Report',
    #       alt_txt='test image',
    #       file='test.png'
    
    # )
    # print(responseUploadImg)
    # print(responseUploadImg.get("file").get("permalink"))
    
    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": 'Wait a moment, i´m thinking :hourglass:'
                }
            },
            #  {
            #     "type": "image",
            #     "block_id": "b++",
            #     "image_url": responseUploadImg.get("file").get("permalink"),
            #     "alt_text": "image"
            # },
            ],
        thread_ts=thread_ts,
        text=f"Hey there!"
    )

    gpt_response = ""

    if cantData == "1":
        newText = f'{body["event"]["text"]}, Return only the query, it should be inside parentheses, following this format: (query).'
        try:
            gpt_response = agent_executor.run(newText)
        except Exception as e:
            say("Error in process")
            print(e)
        cantData = ""
    else:
        try:
            gpt_response = agent_executor.run({body["event"]["text"]})
        except Exception as e:
            say("Error in process")
            print(e)
        cantData = ""

    
    # say(text="Hello", ) 

    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f'Your answer is: *{gpt_response}*'
                }
            }],
        thread_ts=thread_ts,
        text=f"Hey there!"
    )


if __name__ == "__main__":
    SocketModeHandler(app, slackAppToken).start()
    appFlask.run(debug=True)
    app.start(3000)
