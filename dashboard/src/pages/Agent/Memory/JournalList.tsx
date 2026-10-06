/**
 * JournalList.tsx — story-style activity timeline.
 *
 * User-facing Agent activity timeline, not an audit log. Pipeline actions such
 * as capture/extract/page_regen are grouped into story cards by time window,
 * while key events such as promote/reject/deprecate remain standalone.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Card, Empty, Pagination, Select, Skeleton, Space, Tag } from "antd";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";

import {
  memoryDashboardApi,
  type ExtractRunStats,
  type JournalItem,
  type ListJournalBody,
} from "../../../api/modules/memoryDashboard";
import { useServerTimezone } from "../../../hooks/useServerTimezone";
import {
  calendarDaysAgo,
  formatServerHourMinute,
  formatServerYmd,
} from "../../../utils/formatMessageTime";

const PAGE_SIZE = 30;

const ACTION_OPTIONS = [
  { value: "", labelKey: "memory.journal.filter.all", label: "全部记录" },
  {
    value: "extract_run",
    labelKey: "memory.journal.filter.extractRun",
    label: "提取运行",
  },
  { value: "promote", labelKey: "memory.journal.filter.promote", label: "采纳" },
  { value: "reject", labelKey: "memory.journal.filter.reject", label: "忽略" },
  {
    value: "deprecate",
    labelKey: "memory.journal.filter.deprecate",
    label: "弃用",
  },
  { value: "create", labelKey: "memory.journal.filter.create", label: "新建" },
  { value: "user_edit", labelKey: "memory.journal.filter.edit", label: "编辑" },
  {
    value: "page_regen",
    labelKey: "memory.journal.filter.pageRegen",
    label: "刷新主题",
  },
];

const ACTION_COLOR: Record<string, string> = {
  extract_run: "cyan",
  capture: "default",
  extract: "blue",
  promote: "purple",
  reject: "red",
  deprecate: "volcano",
  page_regen: "geekblue",
  create: "green",
  update: "blue",
  user_edit: "blue",
  merge: "gold",
};

const ACTION_HEX: Record<string, string> = {
  extract_run: "#13c2c2",
  capture: "#8c8c8c",
  extract: "#1677ff",
  promote: "#722ed1",
  reject: "#ff4d4f",
  deprecate: "#fa541c",
  page_regen: "#2f54eb",
  create: "#52c41a",
  update: "#1677ff",
  user_edit: "#1677ff",
  merge: "#faad14",
};

/** Internal pipeline actions that should be aggregated into one story. */
const PIPELINE_ACTIONS = new Set(["capture", "extract", "page_regen"]);
/** Maximum time gap within one aggregate group. */
const GROUP_GAP_MS = 60_000;

interface Props {
  agentId: string;
}

export default function JournalList({ agentId }: Props) {
  const { t } = useTranslation();
  const timeZone = useServerTimezone();
  const [items, setItems] = useState<JournalItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const load = useCallback(async () => {
    setLoading(true);
    const body: ListJournalBody = {
      offset: (page - 1) * PAGE_SIZE,
      limit: PAGE_SIZE,
    };
    if (action) body.action = action;
    try {
      const r = await memoryDashboardApi.listJournal(agentId, body);
      setItems(r.items);
      setTotal(r.total);
    } finally {
      setLoading(false);
    }
  }, [agentId, page, action]);

  useEffect(() => {
    if (!agentId) return;
    void load();
  }, [agentId, load]);

  const days = useMemo(
    () => buildDays(items, timeZone, t),
    [items, timeZone, t],
  );

  return (
    <Card size="small">
      <Space style={{ marginBottom: 16 }} wrap>
        <span style={{ color: "#595959" }}>
          {t("memory.journal.filterLabel", "筛选类型")}:
        </span>
        <Select
          style={{ width: 180 }}
          value={action}
          onChange={(v) => {
            setAction(v);
            setPage(1);
          }}
          options={ACTION_OPTIONS.map((o) => ({
            value: o.value,
            label: t(o.labelKey, o.label),
          }))}
        />
      </Space>

      {loading && items.length === 0 ? (
        <Skeleton active />
      ) : items.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t("memory.journal.empty", "暂无整理记录")}
        />
      ) : (
        <div>
          {days.map((day) => (
            <DaySection
              key={day.label}
              day={day}
              timeZone={timeZone}
              expanded={expanded}
              onToggle={(key) => setExpanded((s) => ({ ...s, [key]: !s[key] }))}
            />
          ))}
        </div>
      )}

      <div style={{ marginTop: 16, textAlign: "right" }}>
        <Pagination
          current={page}
          pageSize={PAGE_SIZE}
          total={total}
          showSizeChanger={false}
          onChange={setPage}
        />
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Child component: one section per day.
// ---------------------------------------------------------------------------

interface DayBucket {
  label: string;
  groups: Group[];
}

interface Group {
  /** Stable key for expansion state. */
  key: string;
  /** Representative timestamp shown on the left. */
  timestamp: string;
  /** Internal details, one item for a single event. */
  items: JournalItem[];
  /** Whether this is an aggregated pipeline story. */
  isPipelineGroup: boolean;
}

function DaySection({
  day,
  timeZone,
  expanded,
  onToggle,
}: {
  day: DayBucket;
  timeZone: string;
  expanded: Record<string, boolean>;
  onToggle: (key: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <div style={{ marginBottom: 20 }}>
      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: "#8c8c8c",
          margin: "4px 0 12px",
          letterSpacing: 0.3,
        }}
      >
        {day.label}
        <span style={{ marginLeft: 8, fontWeight: 400 }}>
          ·{" "}
          {t("memory.journal.itemCount", "{{n}} 项", {
            n: day.groups.length,
          })}
        </span>
      </div>
      <div style={{ position: "relative", paddingLeft: 16 }}>
        {/* Timeline vertical line */}
        <div
          style={{
            position: "absolute",
            left: 5,
            top: 4,
            bottom: 4,
            width: 1,
            background: "#f0f0f0",
          }}
        />
        {day.groups.map((g) => (
          <GroupRow
            key={g.key}
            group={g}
            timeZone={timeZone}
            isExpanded={!!expanded[g.key]}
            onToggle={() => onToggle(g.key)}
          />
        ))}
      </div>
    </div>
  );
}

function GroupRow({
  group,
  timeZone,
  isExpanded,
  onToggle,
}: {
  group: Group;
  timeZone: string;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  if (group.isPipelineGroup) {
    return (
      <PipelineStoryRow
        group={group}
        timeZone={timeZone}
        isExpanded={isExpanded}
        onToggle={onToggle}
      />
    );
  }
  // Single standalone event.
  return <SingleEventRow item={group.items[0]} timeZone={timeZone} />;
}

/** Pipeline story card: capture/extract/page_regen aggregation. */
function PipelineStoryRow({
  group,
  timeZone,
  isExpanded,
  onToggle,
}: {
  group: Group;
  timeZone: string;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const { t } = useTranslation();
  const summary = pipelineSummary(group.items, t);
  const dotColor = ACTION_HEX["capture"];
  return (
    <div style={{ marginBottom: 10 }}>
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 12,
          cursor: "pointer",
          padding: "6px 8px 6px 0",
          borderRadius: 4,
        }}
        onClick={onToggle}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onToggle();
          }
        }}
        role="button"
        tabIndex={0}
      >
        <span
          style={{
            color: "#8c8c8c",
            fontSize: 12,
            minWidth: 44,
            paddingTop: 2,
          }}
        >
          {formatServerHourMinute(group.timestamp, timeZone)}
        </span>
        <span
          style={{
            position: "relative",
            left: -11,
            marginRight: -6,
            marginTop: 6,
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: dotColor,
            border: "2px solid #fff",
            boxShadow: "0 0 0 1px #d9d9d9",
            flex: "0 0 10px",
          }}
        />
        <div style={{ flex: 1, minWidth: 0, fontSize: 13 }}>
          <Space size={6} wrap>
            <span style={{ color: "#262626" }}>📥 {summary.title}</span>
            {summary.tags.map((tag, idx) => (
              <Tag key={idx} color={tag.color} style={{ margin: 0 }}>
                {tag.text}
              </Tag>
            ))}
          </Space>
        </div>
        <span style={{ color: "#bfbfbf", fontSize: 12, paddingTop: 2 }}>
          {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
      </div>
      {isExpanded && (
        <div
          style={{
            paddingLeft: 60,
            paddingRight: 8,
            paddingBottom: 6,
            borderLeft: "1px dashed transparent",
          }}
        >
          {group.items.map((j) => (
            <DetailLine key={j.id} item={j} timeZone={timeZone} />
          ))}
        </div>
      )}
    </div>
  );
}

/** Standalone key event: promote / reject / deprecate / create / update / merge. */
function SingleEventRow({
  item,
  timeZone,
}: {
  item: JournalItem;
  timeZone: string;
}) {
  const { t } = useTranslation();
  const dotColor = ACTION_HEX[item.action] ?? "#bfbfbf";
  const story = singleEventStory(item);
  const isRun = item.action === "extract_run";
  const runText = isRun ? extractRunSummary(item.after, t) : "";
  const detailText = isRun ? "" : noteToChinese(item.note, t);
  return (
    <div style={{ marginBottom: 10, display: "flex", gap: 12 }}>
      <span
        style={{
          color: "#8c8c8c",
          fontSize: 12,
          minWidth: 44,
          paddingTop: 2,
        }}
      >
        {formatServerHourMinute(item.timestamp, timeZone)}
      </span>
      <span
        style={{
          position: "relative",
          left: -11,
          marginRight: -6,
          marginTop: 6,
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: dotColor,
          border: "2px solid #fff",
          boxShadow: "0 0 0 1px #d9d9d9",
          flex: "0 0 10px",
        }}
      />
      <div style={{ flex: 1, minWidth: 0, fontSize: 13 }}>
        <Space size={6} wrap>
          <span style={{ color: "#262626" }}>{story.icon}</span>
          <Tag
            color={ACTION_COLOR[item.action] ?? "default"}
            style={{ margin: 0 }}
          >
            {actionLabel(item.action, t)}
          </Tag>
          <span style={{ color: "#595959" }}>
            {isRun ? runText : targetText(item, t)}
          </span>
        </Space>
        {detailText ? (
          <div
            style={{
              marginTop: 4,
              fontSize: 12,
              color: "#8c8c8c",
              lineHeight: 1.5,
            }}
          >
            {detailText}
          </div>
        ) : null}
      </div>
    </div>
  );
}

/** Human summary for an ``extract_run`` row, built from its structured stats. */
function extractRunSummary(
  after: ExtractRunStats | null | undefined,
  t: TFunction,
): string {
  const s = after ?? {};
  if (s.failure_reason) {
    if (/no llm|not configured|no model/i.test(s.failure_reason)) {
      return t(
        "memory.journal.run.noModel",
        "未配置提取模型，本次未运行",
      );
    }
    return t("memory.journal.run.failed", "本次提取失败");
  }
  const extracted = s.events_extracted ?? 0;
  if (extracted === 0) {
    return t("memory.journal.run.nothingNew", "扫描 {{n}} 段对话，无新增内容", {
      n: s.events_considered ?? 0,
    });
  }
  const promoted = s.promoted ?? 0;
  const candidates = s.candidates ?? 0;
  if (candidates === 0) {
    return t(
      "memory.journal.run.nothingMemorable",
      "处理 {{n}} 段对话，未发现可记忆的内容",
      { n: extracted },
    );
  }
  return t(
    "memory.journal.run.summary",
    "处理 {{n}} 段对话，生成 {{candidates}} 条草稿，晋升 {{promoted}} 条记忆",
    { n: extracted, candidates, promoted },
  );
}

/** Child row for each pipeline detail in the expanded state. */
function DetailLine({
  item,
  timeZone,
}: {
  item: JournalItem;
  timeZone: string;
}) {
  const { t } = useTranslation();
  const note = noteToChinese(item.note, t);
  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        alignItems: "baseline",
        padding: "3px 0",
        fontSize: 12,
        color: "#8c8c8c",
      }}
    >
      <span style={{ minWidth: 40 }}>
        {formatServerHourMinute(item.timestamp, timeZone)}
      </span>
      <Tag
        color={ACTION_COLOR[item.action] ?? "default"}
        style={{ margin: 0, fontSize: 11 }}
      >
        {actionLabel(item.action, t)}
      </Tag>
      {targetText(item, t) ? (
        <span style={{ color: "#8c8c8c" }}>{targetText(item, t)}</span>
      ) : null}
      {note ? <span style={{ color: "#bfbfbf" }}>— {note}</span> : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Data shaping: flat items -> DayBucket[Group[]].
// ---------------------------------------------------------------------------

function buildDays(
  items: JournalItem[],
  timeZone: string,
  t: TFunction,
): DayBucket[] {
  const groups = aggregate(items);
  const out: DayBucket[] = [];
  for (const g of groups) {
    const diffDays = calendarDaysAgo(g.timestamp, timeZone);
    let label: string;
    if (diffDays === 0) label = t("memory.time.today", "今天");
    else if (diffDays === 1) label = t("memory.time.yesterday", "昨天");
    else if (diffDays > 1 && diffDays < 7)
      label = t("memory.time.daysAgo", "{{n}} 天前", { n: diffDays });
    else label = formatServerYmd(g.timestamp, timeZone);

    const last = out[out.length - 1];
    if (last && last.label === label) {
      last.groups.push(g);
    } else {
      out.push({ label, groups: [g] });
    }
  }
  return out;
}

/**
 * Aggregation rules:
 *   - Backend list is already timestamp DESC.
 *   - Scan forward; PIPELINE_ACTIONS start or join a group within GROUP_GAP_MS.
 *   - Non-pipeline key events become standalone groups.
 */
function aggregate(items: JournalItem[]): Group[] {
  const groups: Group[] = [];
  let cur: Group | null = null;
  for (const it of items) {
    const isPipeline = PIPELINE_ACTIONS.has(it.action);
    if (!isPipeline) {
      if (cur) {
        groups.push(cur);
        cur = null;
      }
      groups.push({
        key: `single-${it.id}`,
        timestamp: it.timestamp,
        items: [it],
        isPipelineGroup: false,
      });
      continue;
    }
    // pipeline action
    if (!cur) {
      cur = {
        key: `grp-${it.id}`,
        timestamp: it.timestamp,
        items: [it],
        isPipelineGroup: true,
      };
      continue;
    }
    const last = cur.items[cur.items.length - 1];
    const gap = Math.abs(
      new Date(last.timestamp).getTime() - new Date(it.timestamp).getTime(),
    );
    if (gap <= GROUP_GAP_MS) {
      cur.items.push(it);
    } else {
      groups.push(cur);
      cur = {
        key: `grp-${it.id}`,
        timestamp: it.timestamp,
        items: [it],
        isPipelineGroup: true,
      };
    }
  }
  if (cur) groups.push(cur);
  return groups;
}

// ---------------------------------------------------------------------------
// Copy generation.
// ---------------------------------------------------------------------------

interface PipelineSummary {
  title: string;
  tags: { text: string; color: string }[];
}

function pipelineSummary(items: JournalItem[], t: TFunction): PipelineSummary {
  let captureN = 0;
  let extractN = 0;
  let regenN = 0;
  for (const it of items) {
    if (it.action === "capture") captureN++;
    else if (it.action === "extract") extractN++;
    else if (it.action === "page_regen") regenN++;
  }
  let title = t("memory.journal.story.default", "整理了一段对话");
  if (captureN > 0 && extractN === 0 && regenN === 0) {
    title = t("memory.journal.story.captured", "记录了 {{capture}} 段对话", {
      capture: captureN,
    });
  } else if (captureN > 0 && extractN > 0 && regenN === 0) {
    title = t(
      "memory.journal.story.capturedExtracted",
      "处理了 {{capture}} 段对话，生成 {{extract}} 条记忆草稿",
      { capture: captureN, extract: extractN },
    );
  } else if (captureN === 0 && extractN > 0 && regenN === 0) {
    title = t("memory.journal.story.extracted", "生成了 {{extract}} 条记忆草稿", {
      extract: extractN,
    });
  } else if (regenN > 0 && extractN === 0 && captureN === 0) {
    title = t("memory.journal.story.regen", "刷新了 {{regen}} 个主题摘要", {
      regen: regenN,
    });
  } else if (captureN > 0 && regenN > 0) {
    title = t(
      "memory.journal.story.capturedRegen",
      "处理了 {{capture}} 段对话，并刷新了 {{regen}} 个主题摘要",
      { capture: captureN, regen: regenN },
    );
  } else if (extractN > 0 && regenN > 0) {
    title = t(
      "memory.journal.story.extractedRegen",
      "生成了 {{extract}} 条记忆草稿，并刷新了 {{regen}} 个主题摘要",
      { extract: extractN, regen: regenN },
    );
  }
  const tags: { text: string; color: string }[] = [];
  if (captureN > 0)
    tags.push({
      text: t("memory.journal.tag.capture", "📥 {{n}} 段对话", { n: captureN }),
      color: "default",
    });
  if (extractN > 0)
    tags.push({
      text: t("memory.journal.tag.extract", "📝 {{n}} 条草稿", { n: extractN }),
      color: "blue",
    });
  if (regenN > 0)
    tags.push({
      text: t("memory.journal.tag.regen", "🔄 {{n}} 次刷新", { n: regenN }),
      color: "geekblue",
    });
  return { title, tags };
}

function singleEventStory(item: JournalItem): { icon: string } {
  switch (item.action) {
    case "extract_run":
      return { icon: item.after?.failure_reason ? "⚠️" : "🔍" };
    case "promote":
      return { icon: "✅" };
    case "reject":
      return { icon: "🚫" };
    case "deprecate":
      return { icon: "🗑️" };
    case "create":
      return { icon: "🆕" };
    case "update":
    case "user_edit":
      return { icon: "✏️" };
    case "merge":
      return { icon: "🔗" };
    default:
      return { icon: "•" };
  }
}

function targetText(j: JournalItem, t: TFunction): string {
  // Backend-enriched target text lets us show the specific acted-on item; otherwise fall back to type.
  if (j.target_summary)
    return t("memory.journal.target.quoted", "「{{text}}」", {
      text: j.target_summary,
    });
  if (j.target_atom_id) return t("memory.journal.target.atom", "一条记忆");
  if (j.target_entity_id) return t("memory.journal.target.entity", "一个主题");
  if (j.target_candidate_id)
    return t("memory.journal.target.candidate", "一条草稿");
  return "";
}

function actionLabel(action: string, t: TFunction): string {
  switch (action) {
    case "extract_run":
      return t("memory.journal.label.extractRun", "提取运行");
    case "capture":
      return t("memory.journal.label.capture", "记录对话");
    case "extract":
      return t("memory.journal.label.extract", "生成草稿");
    case "promote":
      return t("memory.journal.label.promote", "采纳");
    case "reject":
      return t("memory.journal.label.reject", "忽略");
    case "deprecate":
      return t("memory.journal.label.deprecate", "弃用");
    case "page_regen":
      return t("memory.journal.label.pageRegen", "刷新主题");
    case "create":
      return t("memory.journal.label.create", "创建");
    case "update":
    case "user_edit":
      return t("memory.journal.label.update", "更新");
    case "merge":
      return t("memory.journal.label.merge", "合并");
    default:
      return action;
  }
}

/**
 * Convert backend notes, often English dev logs, into user-facing Chinese.
 * Known English patterns are translated, user-provided Chinese reasons are
 * preserved, and other dev logs return null to avoid mixed-language noise.
 */
function noteToChinese(
  note: string | null | undefined,
  t: TFunction,
): string | null {
  const s = (note ?? "").trim();
  if (!s) return null;

  // Entity resolution during promotion: linked existing topic or created new topic.
  let m = /^entity resolved via alias ['"](.+)['"]$/i.exec(s);
  if (m)
    return t("memory.journal.note.linkedTopic", "关联到已有主题「{{name}}」", {
      name: m[1],
    });
  m = /^no existing entity matched ['"](.+)['"];?\s*will create$/i.exec(s);
  if (m)
    return t("memory.journal.note.newTopic", "新建主题「{{name}}」", {
      name: m[1],
    });

  // Deprecation-related notes.
  if (/^atom deprecated without replacement/i.test(s))
    return t("memory.journal.note.deprecatedNoReplacement", "弃用（无替代记忆）");
  m = /^semantic duplicate; superseded by /i.exec(s);
  if (m) return t("memory.journal.note.semanticDuplicate", "语义重复，已被合并");

  // Preserve user-provided Chinese reasons.
  if (/[一-鿿]/.test(s)) return s;

  // Hide other English dev logs.
  return null;
}
