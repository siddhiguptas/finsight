from typing import Any, Optional
from dataclasses import dataclass, field

@dataclass
class NewsFilterBuilder:
    conditions: list[str] = field(default_factory=list)
    params: list[Any] = field(default_factory=list)
    param_counter: int = 1

    def _register_param(self, value: Any) -> str:
        self.params.append(value)
        placeholder = f"${self.param_counter}"
        self.param_counter += 1
        return placeholder

    def add_impact_levels(self, levels: list[str]) -> "NewsFilterBuilder":
        if levels:
            placeholders = ", ".join(self._register_param(l) for l in levels)
            self.conditions.append(f"nsa.impact_level IN ({placeholders})")
        return self

    def add_time_window(self, hours: int) -> "NewsFilterBuilder":
        if hours:
            self.conditions.append(f"na.published_at >= NOW() - INTERVAL '{hours} hours'")
        return self

    def add_min_reliability(self, min_score: float) -> "NewsFilterBuilder":
        if min_score > 0:
            self.conditions.append(
                f"COALESCE(nrs.reliability_score, src.accuracy_24h) >= {self._register_param(min_score)}"
            )
        return self

    def add_sentiments(self, labels: list[str]) -> "NewsFilterBuilder":
        if labels:
            placeholders = ", ".join(self._register_param(l) for l in labels)
            self.conditions.append(f"nsa.sentiment_label IN ({placeholders})")
        return self

    def add_tickers(self, tickers: list[str]) -> "NewsFilterBuilder":
        if tickers:
            self.conditions.append(f"nst.ticker = ANY({self._register_param(tickers)})")
        return self

    def add_sectors(self, sectors: list[str]) -> "NewsFilterBuilder":
        if sectors:
            placeholders = ", ".join(self._register_param(s) for s in sectors)
            self.conditions.append(f"nsect.sector_name IN ({placeholders})")
        return self

    def add_sources(self, sources: list[str]) -> "NewsFilterBuilder":
        if sources:
            placeholders = ", ".join(self._register_param(s) for s in sources)
            self.conditions.append(f"na.source_name IN ({placeholders})")
        return self

    def build_where(self) -> str:
        base = ["na.is_deleted = FALSE", "na.is_duplicate = FALSE"]
        all_conditions = base + self.conditions
        return " AND ".join(all_conditions)

    def get_params(self) -> list[Any]:
        return self.params

    def build_order_by(self, sort_by: str, sort_order: str) -> str:
        column_map = {
            "published_at": "na.published_at",
            "impact_score": "nsa.impact_score",
            "reliability_score": "COALESCE(nrs.reliability_score, src.accuracy_24h)",
        }

        column = column_map.get(sort_by, "na.published_at")
        direction = "DESC" if sort_order.lower() == "desc" else "ASC"

        return f"{column} {direction}"
