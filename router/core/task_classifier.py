"""
Task Classifier for the LLMLab LLM Router.

Responsibilities:
- Phase 1: YAML keyword-based task detection (weighted scoring)
- Phase 2: Optional local LLM classifier
- Provide a unified classify() API for the RoutingEngine
- Provide explainability for debugging
"""

from typing import Dict, Any, List, Optional, Tuple


class TaskClassifier:
    """
    Task classifier for routing decisions.
    Exported.
    """

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._tasks = config.get("tasks", {})
        self._default = config.get("default_task", "general")

        # Optional: enable LLM-based classification
        self._use_llm = config.get("classifier", {}).get("enabled", False)

        # Optional: debugging
        self._debug = config.get("classifier", {}).get("debug", False)

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def classify(self, messages: List[Dict[str, Any]]) -> str:
        """
        Determine the task type for a given message list.
        Exported.
        """
        # 1. Keyword-based scoring
        task, score = self._keyword_score(messages)
        if task:
            if self._debug:
                print(f"[classifier] keyword match → {task} (score={score})")
            return task

        # 2. Optional LLM-based classification
        if self._use_llm:
            llm_task = self._llm_classify(messages)
            if llm_task:
                if self._debug:
                    print(f"[classifier] llm classify → {llm_task}")
                return llm_task

        # 3. Fallback
        if self._debug:
            print(f"[classifier] fallback → {self._default}")
        return self._default

    # ------------------------------------------------------------
    # Weighted Keyword Scoring
    # ------------------------------------------------------------

    def _keyword_score(self, messages: List[Dict[str, Any]]) -> Tuple[Optional[str], float]:
        """
        Weighted keyword scoring:
        - Each task has:
            keywords: [ "foo", "bar" ]
            negative_keywords: [ "not", "exclude" ]
            weight: float
        - Score = (#matches * weight) - (#negatives * penalty)
        - Highest score wins
        """
        if not messages:
            return None, 0.0

        last_msg = messages[-1]["content"].lower()

        best_task = None
        best_score = 0.0

        for task_name, cfg in self._tasks.items():
            keywords = cfg.get("keywords", [])
            negatives = cfg.get("negative_keywords", [])
            weight = cfg.get("weight", 1.0)
            penalty = cfg.get("penalty", 1.0)

            score = 0.0

            # Positive keywords
            for kw in keywords:
                if kw.lower() in last_msg:
                    score += weight

            # Negative keywords
            for n in negatives:
                if n.lower() in last_msg:
                    score -= penalty

            if score > best_score:
                best_score = score
                best_task = task_name

        return best_task, best_score

    # ------------------------------------------------------------
    # Optional LLM Classifier
    # ------------------------------------------------------------

    def _llm_classify(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """
        Use a local LLM to classify the task.
        Stub for now.
        Internal.
        """
        # Placeholder: actual LLM call will be implemented later
        return None

