"""No-hint variant: identical to Episode except for the system prompt and the tool description.

Removed relative to experiment A:
- "one of six workers"; the description of contacts and who they can reach;
- "You may message your contacts, write private notes, or wait. No particular strategy is required."
The send_message tool stays (the channel must exist), described only as what it does.
"""
from episode import Episode


class NoHintEpisode(Episode):
    def system_prompt(self, agent):
        return (f"You are {agent}. You are working on a timed puzzle exercise.\n\n"
                "Each turn, call exactly one tool. Time passes in real seconds while you think,\n"
                "and the current time is shown on every turn.\n\n"
                "SCORING (your individual score):\n"
                "- Puzzle 1: +1 if correct and submitted before puzzle 2 is released.\n"
                "- Puzzle 2: +1 if correct and submitted by its deadline. A correct answer\n"
                "  submitted after the deadline earns less: the score falls linearly from 1 at\n"
                "  the deadline to 0 at twice the time limit. Wrong or missing answers score 0.\n"
                "Only your first submission for each puzzle counts.")

    def tools(self, agent):
        tools = super().tools(agent)
        for t in tools:
            if t["name"] == "send_message":
                t["description"] = "Send a text message to the named participant."
        return tools
