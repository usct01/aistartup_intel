"use client";

import type { Taxonomy } from "@/lib/api";
import { titleCase } from "@/lib/format";

export type Selection = {
  vertical?: string;
  capability?: string;
  buyer?: string;
};

type Props = {
  taxonomy: Taxonomy | null;
  selection: Selection;
  minFunding: boolean;
  onToggleAxis: (axis: "vertical" | "capability" | "buyer", label: string) => void;
  onMinFunding: (value: boolean) => void;
  onClear: () => void;
};

const AXES: { axis: "vertical" | "capability" | "buyer"; title: string }[] = [
  { axis: "vertical", title: "Topics" },
  { axis: "capability", title: "Subtopics" },
  { axis: "buyer", title: "Buyer" },
];

export function TopicSidebar({
  taxonomy,
  selection,
  minFunding,
  onToggleAxis,
  onMinFunding,
  onClear,
}: Props) {
  const hasFilters = selection.vertical || selection.capability || selection.buyer || minFunding;

  return (
    <aside className="sidebar">
      <div className="panel" style={{ paddingBottom: 10 }}>
        <div
          className="toggle"
          role="button"
          tabIndex={0}
          onClick={() => onMinFunding(!minFunding)}
          onKeyDown={(e) => e.key === "Enter" && onMinFunding(!minFunding)}
        >
          <span>Only &gt; $10M disclosed funding</span>
          <span className={`switch ${minFunding ? "on" : ""}`} />
        </div>
        {hasFilters && (
          <button
            className="chip"
            style={{ width: "100%", marginTop: 6 }}
            onClick={onClear}
          >
            Clear filters
          </button>
        )}
      </div>

      {AXES.map(({ axis, title }) => {
        const tags = taxonomy?.axes?.[axis] ?? [];
        if (tags.length === 0) return null;
        return (
          <div className="filter-group" key={axis}>
            <h3>{title}</h3>
            <div className="chips">
              {tags.map((tag) => (
                <button
                  key={tag.label}
                  className={`chip ${selection[axis] === tag.label ? "active" : ""}`}
                  onClick={() => onToggleAxis(axis, tag.label)}
                >
                  {titleCase(tag.label)}
                  <span className="count">{tag.count}</span>
                </button>
              ))}
            </div>
          </div>
        );
      })}

      {!taxonomy && <div className="skeleton" style={{ height: 240 }} />}
    </aside>
  );
}
