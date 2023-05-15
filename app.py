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
TABLE_PATH = './gpt-output.csv'

# Langchain objects
# -----------------

# Database
db = SQLDatabase.from_uri(conn_string)

# Model
llm = ChatOpenAI(model_name='gpt-3.5-turbo')

# Agent
toolkit = SQLDatabaseToolkit(db=db, llm=llm, verbose=False)
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
    say("Ask me something about Kiwi's data")


@app.action("button_multiple")
def action_button_click(body, ack, say):
    ack()
    global cantData
    cantData = "1"
    say("Ask me something about Kiwi's data")

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
    
    say(
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": 'Wait a moment, I am thinking :hourglass:'
                }
            },
        ],
        thread_ts = thread_ts
    )

    gpt_response = ""

    if cantData == "1":
        newText = f"""{body["event"]["text"]}. The answer must be the query \
            used to answer this question without limit, it should be inside \
            parentheses, following this format: (query)."""

        try:
            # Run user question into SQL Agent, with GPT core
            gpt_response = agent_executor.run(newText)

            # Clean the model's output
            print(gpt_response)
            query = re.findall(REGEX_PATTERN, gpt_response)[0]
            query = re.sub(r' \bLIMIT\b.*$', "", query)

            # Call the data in SQL
            df = pd.read_sql_query(query, engine)

            # Save the data into CSV file
            df.to_csv(TABLE_PATH, index=False)
            # gpt_response = df.to_markdown(index=False)

            # Upload file into AthenSQL channel
            _ = client.files_upload_v2(
                channels = CHANNEL_ID,
                initial_comment = 'The result to your inquiry is (CSV file):',
                file = TABLE_PATH,
                thread_ts = thread_ts
            )

        except Exception as e:
            say("Sorry, your inquiry couldn't be processed")
            print(e)
        cantData = ""
    else:

        try:
            # Pass the question to the SQL agent
            gpt_response = agent_executor.run(body["event"]["text"])
            print(gpt_response)

        except Exception as e:
            say("Error in process")
            print(e)
        cantData = ""

        # Return the model's output
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
