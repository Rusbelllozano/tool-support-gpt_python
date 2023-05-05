# Base libraries
# Langchain and OpenAI
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
# import re
# import string
# import hashlib
# import datetime as dt
# from dateutil.relativedelta import relativedelta


# User libraries

load_dotenv()

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
    # verbose=True
)


@app.message("hello")
def message_hello(client, message, say):
    print('activado el entorno')
    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Hola, estas son mis opciones principales :smile: *Tener en cuenta*, requiero tiempo despues de presionar un botón para responder"
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
                                        "text": "Describe the user table"
                                    },
                                    "style": "primary",
                                    "value": "click_me_1",
                                    "style": "primary",
                                    "action_id": "button_click"
                                },
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Enseñarme algo nuevo"
                                    },
                                    "action_id": "button_learn_something"
                                }
                            ]
            }
        ],
        text=f"Hey there <@{message['user']}>!"
    )


@app.action("button_learn_something")
def action_button_click(body, ack, say):
    # Acknowledge the action
    ack()
    response = agent_executor.run(
        "Remember this: if a client try to create a new account but exist a same email in table users show a alert message, the user have to change the phone number or is trying to suplant")
    print(response)
    say(response)


@app.action("button_click")
def action_button_click(body, ack, say):
    # Acknowledge the action
    ack()
    response = agent_executor.run("Describe the users table")
    print(response)
    say(response)


@app.event("app_mention")
def event_test(body, say, logger):
    logger.info(body)
    say("What's up?")


@app.command("/echo")
def repeat_text(ack, body, respond, command):
    # Acknowledge command request
    ack()
    respond(f"<@{body['user_id']}>{command['text'] }")


@app.event("message")
def handle_message_events(body, logger):
    print(body[event][text])
    logger.info(body)


@app.command("/hello-bolt-python")
async def command(ack, body, respond):
    await ack()
    await respond(f"Hi tessst <@{body['user_id']}>!")

if __name__ == "__main__":
    SocketModeHandler(app, slackAppToken).start()
    app.start(3000)
