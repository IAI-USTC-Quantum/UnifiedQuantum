import { useState } from "react";
import api from "../hooks/useApi";

interface DemoResult {
  input: { case: string; qubits: number; phase: number };
  execution: string;
  bit_order: string;
  originir: string;
  probabilities: Record<string, number>;
  probability_sum: number;
  max_probability_error: number;
  wall_seconds: number;
}

export function LocalDemo() {
  const [preset, setPreset] = useState("ghz");
  const [qubits, setQubits] = useState(4);
  const [phase, setPhase] = useState(Math.PI / 2);
  const [result, setResult] = useState<DemoResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const response = await api.post<DemoResult>("/demo/simulate", { case: preset, qubits, phase });
      setResult(response.data);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy(false);
    }
  }

  function download() {
    if (!result) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `uniqc-${result.input.case}-${result.input.qubits}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return <section style={{ maxWidth: 1100 }}>
    <h1>Local quantum lab</h1>
    <p style={{ color: "var(--text-muted)" }}>Prepare a quantum state and inspect its exact native simulation probabilities.</p>
    <fieldset className="card" disabled={busy} style={{ display: "flex", flexWrap: "wrap", alignItems: "end", gap: 20 }}>
      <legend>Experiment</legend>
      <label>State<br /><select aria-label="State" value={preset} onChange={event => { setPreset(event.target.value); setResult(null); }}>
        <option value="ghz">GHZ entanglement</option><option value="w">W state</option><option value="ramsey">Ramsey interference</option>
      </select></label>
      <label>Qubits<br /><input aria-label="Qubits" type="number" min={2} max={8} step={1} value={qubits}
        onChange={event => { setQubits(Number(event.target.value)); setResult(null); }} /></label>
      {preset === "ramsey" && <label>Phase (radians)<br /><input aria-label="Phase" type="number" min={-2 * Math.PI} max={2 * Math.PI} step={0.1} value={phase}
        onChange={event => { setPhase(Number(event.target.value)); setResult(null); }} /></label>}
      <button className="btn btn-primary" onClick={run} disabled={busy || !Number.isInteger(qubits) || qubits < 2 || qubits > 8 || !Number.isFinite(phase) || Math.abs(phase) > 2 * Math.PI}>
        {busy ? "Simulating…" : "Run simulation"}
      </button>
    </fieldset>
    {error && <p role="alert" style={{ color: "var(--error)" }}>{error}</p>}
    {result && <>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 16, margin: "24px 0" }}>
        <div className="card">Probability sum<br /><strong>{result.probability_sum.toFixed(10)}</strong></div>
        <div className="card">Maximum error vs analytic result<br /><strong>{result.max_probability_error.toExponential(2)}</strong></div>
        <div className="card">Local execution<br /><strong>{result.wall_seconds.toFixed(3)} s</strong></div>
        <button className="btn btn-ghost" onClick={download}>Export result JSON</button>
      </div>
      <div className="card">
        <h2>Measurement probabilities</h2>
        <p style={{ color: "var(--text-muted)" }}>{result.execution}. {result.bit_order}.</p>
        <div style={{ maxHeight: 420, overflowY: "auto" }}>
          {Object.entries(result.probabilities).sort(([a], [b]) => a.localeCompare(b)).map(([bits, probability]) => <div key={bits}
            style={{ display: "grid", gridTemplateColumns: "100px 1fr 100px", gap: 12, alignItems: "center", margin: "8px 0" }}>
            <code>{bits}</code>
            <div style={{ background: "var(--border)", borderRadius: 4, height: 16 }}><div
              style={{ background: "var(--accent)", height: "100%", borderRadius: 4, width: `${100 * probability}%` }} /></div>
            <span>{(100 * probability).toFixed(4)}%</span>
          </div>)}
        </div>
      </div>
      <div className="card" style={{ marginTop: 24 }}><h2>Executed circuit</h2><pre style={{ overflow: "auto" }}>{result.originir}</pre></div>
    </>}
  </section>;
}
