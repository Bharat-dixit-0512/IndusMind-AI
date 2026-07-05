"use client";

import { useCallback, useEffect, useState } from "react";
import ReactFlow, {
  Background, Controls, MiniMap, BackgroundVariant,
  type Node, type Edge,
} from "reactflow";
import "reactflow/dist/style.css";
import { fetchGraph } from "@/lib/api";
import { Network, RefreshCw, Info } from "lucide-react";

// Color map per node type
const TYPE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  Machine:           { bg: "#0f2d45", border: "#3b82f6", text: "#60a5fa" },
  Engineer:          { bg: "#1a1f35", border: "#6366f1", text: "#a5b4fc" },
  MaintenanceRecord: { bg: "#0f2820", border: "#10b981", text: "#34d399" },
  InspectionReport:  { bg: "#1f1a10", border: "#f59e0b", text: "#fbbf24" },
  Failure:           { bg: "#2a0f0f", border: "#ef4444", text: "#f87171" },
  SOP:               { bg: "#1a1225", border: "#8b5cf6", text: "#c4b5fd" },
  Location:          { bg: "#0f1f1a", border: "#14b8a6", text: "#2dd4bf" },
  SparePart:         { bg: "#1f1205", border: "#f97316", text: "#fb923c" },
};

// Custom node renderer
function CustomNode({ data }: { data: { label: string; type?: string } }) {
  const type = data.type ?? "Machine";
  const colors = TYPE_COLORS[type] ?? TYPE_COLORS.Machine;
  return (
    <div className="px-3 py-2.5 rounded-xl text-center min-w-[120px] max-w-[160px] shadow-lg"
      style={{ background: colors.bg, border: `1.5px solid ${colors.border}`, boxShadow: `0 0 12px ${colors.border}30` }}>
      <p className="text-xs font-bold mb-0.5" style={{ color: colors.text }}>{type}</p>
      <p className="text-xs text-slate-300 leading-tight break-words">{String(data.label).replace(`${type}: `, "")}</p>
    </div>
  );
}

const nodeTypes = { default: CustomNode };

// Build RF nodes / edges from API graph data
function buildRFGraph(apiNodes: { id: string; type: string; data: { label: string } }[], apiEdges: { id: string; source: string; target: string; label: string }[]) {
  // Simple auto-layout: group by type in columns
  const typeGroups: Record<string, number[]> = {};
  apiNodes.forEach((n, i) => {
    if (!typeGroups[n.type]) typeGroups[n.type] = [];
    typeGroups[n.type].push(i);
  });

  const rfNodes: Node[] = [];
  let col = 0;
  for (const type of Object.keys(typeGroups)) {
    const indices = typeGroups[type];
    indices.forEach((idx, row) => {
      const n = apiNodes[idx];
      rfNodes.push({
        id: n.id,
        type: "default",
        position: { x: col * 220, y: row * 110 + 40 },
        data: { ...n.data, type: n.type },
      });
    });
    col++;
  }

  const rfEdges: Edge[] = apiEdges.map(e => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    style: { stroke: "rgba(148,163,184,0.3)", strokeWidth: 1.5 },
    labelStyle: { fill: "#64748b", fontSize: 9, fontFamily: "monospace" },
    labelBgStyle: { fill: "rgba(5,7,15,0.9)", stroke: "rgba(255,255,255,0.06)" },
    labelBgPadding: [3, 5] as [number, number],
    animated: true,
  }));

  return { rfNodes, rfEdges };
}

const LEGEND = Object.entries(TYPE_COLORS).map(([type, c]) => ({ type, ...c }));

export default function GraphPage() {
  const [rfNodes, setRfNodes] = useState<Node[]>([]);
  const [rfEdges, setRfEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Node | null>(null);

  const loadGraph = useCallback(() => {
    setLoading(true);
    fetchGraph()
      .then(data => {
        const { rfNodes: n, rfEdges: e } = buildRFGraph(
          data.nodes ?? [],
          data.relationships ?? []
        );
        setRfNodes(n);
        setRfEdges(e);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount, not derived render state
    loadGraph();
  }, [loadGraph]);

  return (
    <div className="flex flex-col h-screen p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "linear-gradient(135deg, #3b82f6, #1d4ed8)" }}>
              <Network className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-slate-100">Knowledge Graph</h1>
          </div>
          <p className="text-sm text-slate-500 mt-1 ml-11">Live Neo4j graph — Centurion Petrochemical Plant Train 2</p>
        </div>
        <button onClick={loadGraph} className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm text-slate-300 transition-all"
          style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* Main graph canvas */}
        <div className="flex-1 rounded-2xl overflow-hidden" style={{ background: "#05070f", border: "1px solid rgba(255,255,255,0.06)" }}>
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="w-10 h-10 rounded-full border-2 border-blue-500 border-t-transparent animate-spin mx-auto mb-3" />
                <p className="text-sm text-slate-500">Loading knowledge graph…</p>
              </div>
            </div>
          ) : (
            <ReactFlow
              nodes={rfNodes}
              edges={rfEdges}
              nodeTypes={nodeTypes}
              onNodeClick={(_, node) => setSelected(node)}
              fitView
              fitViewOptions={{ padding: 0.15 }}
              minZoom={0.3}
              maxZoom={2.5}>
              <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="rgba(255,255,255,0.04)" />
              <Controls showInteractive={false} style={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.06)" }} />
              <MiniMap nodeColor={n => {
                const t = (n.data as { type?: string }).type ?? "Machine";
                return TYPE_COLORS[t]?.border ?? "#3b82f6";
              }} style={{ background: "#0a0f1e", border: "1px solid rgba(255,255,255,0.06)" }} />
            </ReactFlow>
          )}
        </div>

        {/* Side panel */}
        <div className="w-56 flex flex-col gap-4">
          {/* Legend */}
          <div className="glass-card rounded-2xl p-4">
            <p className="text-xs font-semibold text-slate-400 mb-3">Node Types</p>
            <div className="space-y-2">
              {LEGEND.map(l => (
                <div key={l.type} className="flex items-center gap-2.5">
                  <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ background: l.bg, border: `1.5px solid ${l.border}` }} />
                  <span className="text-xs text-slate-400">{l.type}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Node detail */}
          {selected && (
            <div className="glass-card rounded-2xl p-4 flex-1 overflow-y-auto">
              <div className="flex items-center gap-2 mb-3">
                <Info className="w-4 h-4 text-blue-400" />
                <p className="text-xs font-semibold text-slate-400">Selected Node</p>
              </div>
              <p className="text-xs font-bold mb-2" style={{ color: TYPE_COLORS[(selected.data as { type?: string }).type ?? "Machine"]?.text }}>
                {String((selected.data as { type?: string }).type)}
              </p>
              <div className="space-y-1.5">
                {Object.entries(selected.data as Record<string, unknown>)
                  .filter(([k]) => k !== "label" && k !== "type")
                  .map(([k, v]) => (
                    <div key={k}>
                      <p className="text-xs text-slate-600 capitalize">{k.replace(/_/g, " ")}</p>
                      <p className="text-xs text-slate-300 break-words">{String(v)}</p>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="glass-card rounded-2xl p-4">
            <p className="text-xs font-semibold text-slate-400 mb-2">Graph Stats</p>
            <p className="text-2xl font-bold text-blue-400">{rfNodes.length}</p>
            <p className="text-xs text-slate-600">Nodes</p>
            <p className="text-2xl font-bold text-emerald-400 mt-2">{rfEdges.length}</p>
            <p className="text-xs text-slate-600">Relationships</p>
          </div>
        </div>
      </div>
    </div>
  );
}
