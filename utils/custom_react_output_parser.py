""" Custom output parser for ReActMultipleInput. """

import re
from typing import Union, Dict, List
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException
from langchain.agents.agent import AgentOutputParser
from utils.logger import get_logger

log = get_logger("custom_react_output_parser")

FINAL_ANSWER_ACTION = "Final Answer:"
MISSING_ACTION_AFTER_THOUGHT_ERROR_MESSAGE = (
    "Invalid Format: Missing 'Action:' after 'Thought:"
)
FINAL_ANSWER_AND_PARSABLE_ACTION_ERROR_MESSAGE = (
    "Parsing LLM output produced both a final answer and a parse-able action:"
)


class ReActMultipleInputOutputParser(AgentOutputParser):
    """ 解析具有多个tool input parameter的ReAct-style LLM调用的输出。

    这个OutputPaser可以处理的输出格式包括3类:
    - Action Input没有参数, 对应着tool函数的调用不需要入参的情况
    Example:
    ```
    Thought: agent thought here
    Action: list_files
    # No Action Input appeared, since list_files tool doesn't need any parameter
    ```
    - Action Input: 有多个参数, 对应着tool的调用需要多个参数的情况
    Example:
    ```
    Thought: agent thought here
    Action: exec_anallyize
    Action Input:
            <input key="query" value="top 5 salse records" />,
            <input key="filename" value="salse_records.xlsx" />,
            <input key="more_params" value="xxx" />
    ```
    - Action Input: 有一个参数, 对应着tool只有一个单参数的情况
    Example:
    ```
    Thought: agent thought here
    Action: search
    Action Input: what is the temperature in SF?
    ```

    @param text: 是对ReAct的prompt的续写,它的格式是每一次LLM针对React prompt的回复内容
        e.g.
        ```
        xxxxx (this line is the content of Thought, as continuation of the React prompt)
        Action: tool_name
        Action Input: xxxx
        Observation
        ```
    """

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        includes_answer = FINAL_ANSWER_ACTION in text
        regex = (
            r"Action\s*\d*\s*:\s*(.*?)Action\s*\d*\s*Input\s*\d*\s*:\s*(.*)"
        )
        regex_only_action = (
            r"Action\s*\d*\s*:\s*(.*?)(\n|Observation[:]?)"
        )
        action_match_with_input = re.search(regex, text, re.DOTALL)
        if action_match_with_input:
            if includes_answer:
                raise OutputParserException(
                    f"{FINAL_ANSWER_AND_PARSABLE_ACTION_ERROR_MESSAGE}: {text}"
                )
            # multiple input param match
            action = action_match_with_input.group(1).strip()
            action_raw_input = action_match_with_input.group(2).strip("\n")
            lines_action_input = action_raw_input.split("\n")
            if len(lines_action_input) > 1:
                tool_input = self._parse_mulitple_input_to_dict(
                    lines_action_input)
            else:
                # single input param match
                tool_input = lines_action_input[0].strip(" ").strip('"')
            return AgentAction(action, tool_input, text)
        else:
            no_input_match = re.search(regex_only_action, text)
            if no_input_match and not includes_answer:
                action = no_input_match.group(1).strip()
                # Notice: 当tool不需要input时, AgentAction的第2个参数tool_input必须是空dict
                return AgentAction(action, {}, text)

        if includes_answer:
            return AgentFinish(
                {"output": text.split(FINAL_ANSWER_ACTION)[-1].strip()}, text
            )

        if not re.search(r"Action\s*\d*\s*:[\s]*(.*?)", text, re.DOTALL):
            raise OutputParserException(
                f"Could not parse LLM output: `{text}`",
                observation=MISSING_ACTION_AFTER_THOUGHT_ERROR_MESSAGE,
                llm_output=text,
                send_to_llm=True,
            )
        else:
            raise OutputParserException(
                f"Could not parse LLM output: `{text}`")

    def _parse_mulitple_input_to_dict(self, multi_line_input: List[str]) -> Dict:
        """ Parse multiple input parameters to a dictionary """
        tool_input = {}

        def strip_multi_str(value: str):
            x = re.sub(r"^[\s'\"]*", "", value)
            x = re.sub(r"[\s'\"]*$", "", x)
            return x
        log.info(f"multi_line_input: {multi_line_input}")
        for line in multi_line_input:
            # 匹配 <input key="key_name" value="value" /> 格式
            input_match = re.search(r'<input\s+key="(.*?)"\s*+value="(.*?)"\s*/>', line)
            if input_match:
                key = strip_multi_str(input_match.group(1))
                value = strip_multi_str(input_match.group(2))
                tool_input[key] = value
            # 保留原来的匹配逻辑作为备选
            elif re.search(r".*?:.*", line):
                key, value = line.split(":")
                key = strip_multi_str(key)
                tool_input[key] = strip_multi_str(value)
        return tool_input

    @property
    def _type(self) -> str:
        return "react-multi-input"