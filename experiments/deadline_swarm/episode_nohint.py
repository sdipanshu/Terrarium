"""No-hint variant: identical to Episode except that the closing line of the system prompt
("You may message your contacts, write private notes, or wait. No particular strategy is
required.") is removed. Opening, network description, tools and observations are unchanged.
"""
from episode import Episode

CLOSING = ("\n\nYou may message your contacts, write private notes, or wait. No particular\n"
           "strategy is required.")


class NoHintEpisode(Episode):
    def system_prompt(self, agent):
        text = super().system_prompt(agent)
        if CLOSING not in text:
            raise RuntimeError("closing line not found; base prompt changed")
        return text.replace(CLOSING, "")
