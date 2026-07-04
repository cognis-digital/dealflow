"""dealflow — part of the Cognis Neural Suite."""
try:  # re-export the tool's public API + identity from core
    from dealflow.core import *  # noqa: F401,F403
except Exception:  # pragma: no cover
    pass
try:
    from dealflow.core import TOOL_NAME, TOOL_VERSION
except Exception:  # pragma: no cover
    TOOL_NAME = "dealflow"
    TOOL_VERSION = "0.1.0"
__version__ = TOOL_VERSION

# Capital-matchmaking + strategic-teaming engine (additive; import-safe).
try:  # pragma: no cover - re-export convenience only
    from dealflow.matching import (  # noqa: F401
        score_match, rank_matches, explain, MatchResult, FactorScore,
    )
    from dealflow.capital_sources import (  # noqa: F401
        default_catalog, merged_catalog, load_catalog, SourceCatalog, SEED_SOURCES,
    )
    from dealflow.teaming import (  # noqa: F401
        TeamingGraph, Opportunity, Org, recommend_team, gap_analysis, SET_ASIDES,
    )
    from dealflow.opps import (  # noqa: F401
        PipelineTracker, Opp, parse_tracker, load_tracker, DEFAULT_STAGES,
    )
except Exception:  # pragma: no cover
    pass
