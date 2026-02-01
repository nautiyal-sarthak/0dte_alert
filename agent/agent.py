from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agent.schema import TradeDecision
from agent.prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(model="claude-sonnet-4-20250514")

parser = PydanticOutputParser(pydantic_object=TradeDecision)

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", USER_PROMPT_TEMPLATE + "\n{format_instructions}")
])

chain = prompt | llm | parser


def evaluate_with_agent(features: dict):
    return chain.invoke({
        **features,
        "format_instructions": parser.get_format_instructions()
    })
