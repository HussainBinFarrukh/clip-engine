"use client";

import { useMemo, useRef, useState } from "react";

import type { Signal } from "../lib/api";

// Dark-mode categorical slots 1/2/3 from the validated default palette
// (see the dataviz skill's references/palette.md) plus the app's existing
// muted-ink token for the one signal that's an absence, not a magnitude.
const COLOR_LOUDNESS = "#3987e5";
const COLOR_SPEECH_RATE = "#199e70";
const COLOR_SCENE_CHANGE = "#d95926";
const COLOR_PAUSE = "#aeb8ac";

const CHART_WIDTH = 720;
const ROW_HEIGHT = 56;
const TICK_ROW_HEIGHT = 24;
const MARGIN = { top: 8, right: 12, bottom: 24, left: 12 };

function formatSeconds(ms: number): string {
  return `${(ms / 1000).toFixed(1)}s`;
}

export function SignalsTimeline({
  signals,
  durationMs,
}: {
  signals: Signal[];
  durationMs: number;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoverX, setHoverX] = useState<number | null>(null);

  const loudness = signals.find((s) => s.signal_type === "loudness_rms");
  const speechRate = signals.find((s) => s.signal_type === "speech_rate");
  const sceneChange = signals.find((s) => s.signal_type === "scene_change");
  const pause = signals.find((s) => s.signal_type === "pause");

  const plotWidth = CHART_WIDTH - MARGIN.left - MARGIN.right;
  const xForMs = (ms: number) =>
    durationMs > 0 ? (ms / durationMs) * plotWidth : 0;

  const loudnessPath = useMemo(() => {
    if (!loudness || loudness.points_json.length === 0)
      return { line: "", area: "" };
    const values = loudness.points_json.map((p) => p.value ?? -60);
    const min = Math.min(...values, -60);
    const max = Math.max(...values, -10);
    const yFor = (v: number) =>
      ROW_HEIGHT - ((v - min) / (max - min || 1)) * (ROW_HEIGHT - 4) - 2;

    const coords = loudness.points_json.map((p) => [
      xForMs(p.t_ms),
      yFor(p.value ?? min),
    ]);
    const line = coords
      .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x},${y}`)
      .join(" ");
    const area =
      coords.length > 0
        ? `M${coords[0][0]},${ROW_HEIGHT} ` +
          coords.map(([x, y]) => `L${x},${y}`).join(" ") +
          ` L${coords[coords.length - 1][0]},${ROW_HEIGHT} Z`
        : "";
    return { line, area };
  }, [loudness, durationMs]);

  const speechRatePath = useMemo(() => {
    if (!speechRate || speechRate.points_json.length === 0) return "";
    const values = speechRate.points_json.map((p) => p.value ?? 0);
    const min = 0;
    const max = Math.max(...values, 1);
    const yFor = (v: number) =>
      ROW_HEIGHT - ((v - min) / (max - min || 1)) * (ROW_HEIGHT - 4) - 2;
    return speechRate.points_json
      .map(
        (p, i) =>
          `${i === 0 ? "M" : "L"}${xForMs(p.t_ms)},${yFor(p.value ?? 0)}`,
      )
      .join(" ");
  }, [speechRate, durationMs]);

  if (signals.length === 0) {
    return null;
  }

  const totalHeight =
    MARGIN.top +
    ROW_HEIGHT +
    ROW_HEIGHT +
    TICK_ROW_HEIGHT +
    TICK_ROW_HEIGHT +
    MARGIN.bottom;

  function handleMouseMove(event: React.MouseEvent<SVGSVGElement>) {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const x =
      ((event.clientX - rect.left) / rect.width) * CHART_WIDTH - MARGIN.left;
    setHoverX(Math.max(0, Math.min(plotWidth, x)));
  }

  const hoverMs =
    hoverX !== null && durationMs > 0
      ? (hoverX / plotWidth) * durationMs
      : null;

  return (
    <div className="panel">
      <p className="eyebrow">Signals</p>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${CHART_WIDTH} ${totalHeight}`}
        className="signals-timeline"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoverX(null)}
        role="img"
        aria-label="Loudness, speech rate, scene change, and pause signals over time"
      >
        <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
          {/* Loudness row */}
          <text x={0} y={-2} className="signals-row-label">
            Loudness (dBFS)
          </text>
          <line
            x1={0}
            y1={ROW_HEIGHT}
            x2={plotWidth}
            y2={ROW_HEIGHT}
            className="signals-baseline"
          />
          {loudnessPath.area && (
            <path
              d={loudnessPath.area}
              fill={COLOR_LOUDNESS}
              opacity={0.1}
              stroke="none"
            />
          )}
          {loudnessPath.line && (
            <path
              d={loudnessPath.line}
              fill="none"
              stroke={COLOR_LOUDNESS}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          )}

          {/* Speech rate row */}
          <g transform={`translate(0,${ROW_HEIGHT + 12})`}>
            <text x={0} y={-2} className="signals-row-label">
              Speech rate (wpm)
            </text>
            <line
              x1={0}
              y1={ROW_HEIGHT}
              x2={plotWidth}
              y2={ROW_HEIGHT}
              className="signals-baseline"
            />
            {speechRatePath && (
              <path
                d={speechRatePath}
                fill="none"
                stroke={COLOR_SPEECH_RATE}
                strokeWidth={2}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            )}
            {speechRate?.points_json.map((p) => (
              <circle
                key={p.t_ms}
                cx={xForMs(p.t_ms)}
                cy={ROW_HEIGHT - 4}
                r={4}
                fill={COLOR_SPEECH_RATE}
                stroke="var(--panel)"
                strokeWidth={2}
              >
                <title>
                  {formatSeconds(p.t_ms)}: {p.value} wpm
                </title>
              </circle>
            ))}
          </g>

          {/* Scene change row */}
          <g transform={`translate(0,${2 * ROW_HEIGHT + 24})`}>
            <text x={0} y={-2} className="signals-row-label">
              Scene changes
            </text>
            {sceneChange?.points_json.map((p) => (
              <line
                key={p.t_ms}
                x1={xForMs(p.t_ms)}
                x2={xForMs(p.t_ms)}
                y1={2}
                y2={TICK_ROW_HEIGHT - 2}
                stroke={COLOR_SCENE_CHANGE}
                strokeWidth={2}
              >
                <title>{formatSeconds(p.t_ms)}</title>
              </line>
            ))}
          </g>

          {/* Pause row */}
          <g
            transform={`translate(0,${2 * ROW_HEIGHT + 24 + TICK_ROW_HEIGHT + 12})`}
          >
            <text x={0} y={-2} className="signals-row-label">
              Pauses
            </text>
            {pause?.points_json.map((p) => (
              <rect
                key={p.t_ms}
                x={xForMs(p.t_ms)}
                width={Math.max(2, xForMs(p.duration_ms ?? 0))}
                y={2}
                height={TICK_ROW_HEIGHT - 4}
                fill={COLOR_PAUSE}
                opacity={0.6}
                rx={2}
              >
                <title>
                  {formatSeconds(p.t_ms)}: {p.duration_ms}ms pause
                </title>
              </rect>
            ))}
          </g>

          {hoverX !== null && (
            <line
              x1={hoverX}
              x2={hoverX}
              y1={0}
              y2={2 * ROW_HEIGHT + 24 + 2 * TICK_ROW_HEIGHT + 12}
              className="signals-crosshair"
            />
          )}
        </g>
      </svg>
      {hoverMs !== null && (
        <p className="signals-hover-time">{formatSeconds(hoverMs)}</p>
      )}
    </div>
  );
}
