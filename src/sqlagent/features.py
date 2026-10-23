"""Feature flags so every quality improvement can be switched on/off for ablation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Features:
    few_shot: bool = False        # retrieve top-k similar (question, SQL) pairs from the train split
    repair: bool = False          # feed errors back to the model (up to MAX_ATTEMPTS)
    value_dict: bool = False      # categorical column values + business glossary in the schema
    value_linking: bool = False   # fuzzy-match literals in the question to real DB values
    table_select: bool = False    # LLM picks relevant tables instead of passing the whole schema
    memory: bool = False          # rewrite follow-up questions into standalone ones


# Cumulative presets used for the ablation table.
PRESETS: dict[str, Features] = {
    "baseline": Features(),
    "fewshot": Features(few_shot=True),
    "repair": Features(few_shot=True, repair=True),
    "values": Features(few_shot=True, repair=True, value_dict=True, value_linking=True),
    "tables": Features(few_shot=True, repair=True, value_dict=True, value_linking=True, table_select=True),
    "full": Features(few_shot=True, repair=True, value_dict=True, value_linking=True, table_select=True, memory=True),
}
