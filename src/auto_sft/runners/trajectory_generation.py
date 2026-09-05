"""OpenHands-based trajectory generation (Stage 2 scaffold)."""

import os
from turtle import addshape

from acp.utils import T
from openhands.sdk import LLM, Agent, Conversation, Tool

llm = LLM(
    model="",
    api_key="",
    base_url=""
)

agent = Agent(
    llm=llm,
    tools=[
        Tool(name=Terminal.tool_name),
        Tool(name=Terminal.tool_name),
        Tool(name=Terminal.tool_name),
    ]
)

os.getcwd()
conversation = Conversation(agent=agent, workspace=cwd)

conversation.run()
print("all done")