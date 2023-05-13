#-------------------------------------------------------------------------------
# LIBRARIES
#-------------------------------------------------------------------------------

# Base libraries
import re
import os

# Langchain and OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.llms.openai import OpenAI
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import create_sql_agent


# Slack libraries
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Flask
from flask import Flask

# Data libraries

import pandas as pd
import dataframe_image as dfi
import sqlalchemy as sqla

# Environment variables library
from dotenv import load_dotenv
load_dotenv()

#-------------------------------------------------------------------------------
# Global Variables
# ------------------------------------------------------------------------------

# Enviroment Variables
slackBotToken = os.getenv("SLACK_BOT_TOKEN")
slackAppToken = os.getenv("SLACK_APP_TOKEN")

# App
appFlask = Flask(__name__)
app = App(token=slackBotToken)

# SQL Connection
conn_string = os.getenv("DB_URL")
engine = sqla.create_engine(conn_string)

# Utility variables
REGEX_PATTERN = '\((.+)\)'
CHANNEL_ID = 'D0561LW6E68'
IMAGE_PATH = './gpt-output.csv'

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

#-------------------------------------------------------------------------------
# SLACK FUNCTIONALITY
#-------------------------------------------------------------------------------
@app.message("Hello")
def message_hello(client, message, say):
    user = message['user']
    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<@{user}> welcome to AthenaSQL :smile:, \nplease select which type of inquiry you want to make:"
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
    say("Perfect, you want a specific data point. I will remember that selection")
    say("You can ask me something about Kiwi Financial INC")


@app.action("button_multiple")
def action_button_click(body, ack, say):
    ack()
    global cantData
    cantData = "1"
    say("Perfect, you want a table output. I will remember that selection")
    say("You can ask me something about Kiwi Financial INC")


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
        say(f"Hi! To intiate chat with me please type 'Hello'")
        return

    # say(
    #     blocks=[
    #         {
    #             "type": "section",
    #             "text": {
    #                 "type": "mrkdwn",
    #                 "text": f'Your question is: *{body["event"]["text"]}*'
    #             }
    #         }],
    #     thread_ts=thread_ts
    # )

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
                    "text": 'Wait a moment, I am thinking :hourglass:'
                }
            },
            #  {
            #     "type": "image",
            #     "block_id": "b++",
            #     "image_url": responseUploadImg.get("file").get("permalink"),
            #     "alt_text": "image"
            # },
            ],
        thread_ts=thread_ts
    )

    gpt_response = ""

    if cantData == "1":
        newText = (
            f'{body["event"]["text"]}. The answer must be the query used to answer this question without limit, it should be inside parentheses, following this format: (query).' 
        )
        try:
            gpt_response = agent_executor.run(newText)
            query = re.findall(REGEX_PATTERN, gpt_response)[0]
            df = pd.read_sql_query(query, engine)
            df.to_csv(IMAGE_PATH, index=False)
            gpt_response = df.to_markdown(index=False)
            result = client.files_upload(
                channels = CHANNEL_ID,
                initial_comment = 'CSV table result',
                file = IMAGE_PATH
            )
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
                    "text": f'{gpt_response}'
                }
            }],
        thread_ts=thread_ts,
        text=f"Hey there!"
    )


if __name__ == "__main__":
    SocketModeHandler(app, slackAppToken).start()
    appFlask.run(debug=True)
    app.start(3000)
