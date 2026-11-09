import { useState } from "react";
import api from "../hooks/useApi";

interface QVResult {
  benchmark: string;
  width: number;
  trials: number;
  shots: number;
  base_seed: number;
  backend: string;
  mean_heavy_output_probability: number;
  sigma_mean: number;
  trials_passed: number;
  passed: boolean;
  quantum_volume: number | null;
}

interface ThroughputResult {
  benchmark: string;
  input_set: {
    circuits: number;
    n_qubits: number;
    depth: number;
    shots_per_circuit: number;
    seed: number;
    generator_mode: string;
  };
  backend_id: string;
  timing: {
    compile_seconds: number;
    execute_seconds: number;
    total_seconds: number;
    circuits_per_hour: number;
    compile_circuits_per_hour: number;
    execute_circuits_per_hour: number;
  };
  meets_30000_per_hour: boolean;
  environment: Record<string, unknown>;
}

interface NoiseQRAMResult {
  case: string;
  shots: number;
  seed: number;
  model_sha256: string;
  noisy_counts: Record<string, number>;
  mitigated_counts: Record<string, number>;
  boundary: string;
  expected_value?: number;
  address?: number;
  raw_accuracy?: number;
  mitigated_accuracy?: number;
  ideal_distribution?: Record<string, number>;
  raw_fidelity?: number;
  mitigated_fidelity?: number;
}

function downloadJson(data: unknown, name: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

export function BenchmarksPage() {
  // Quantum Volume
  const [qvWidth, setQvWidth] = useState(4);
  const [qvTrials, setQvTrials] = useState(20);
  const [qvSeed, setQvSeed] = useState(0);
  const [qvResult, setQvResult] = useState<QVResult | null>(null);
  // Throughput
  const [tpCircuits, setTpCircuits] = useState(200);
  const [tpQubits, setTpQubits] = useState(8);
  const [tpDepth, setTpDepth] = useState(6);
  const [tpSeed, setTpSeed] = useState(0);
  const [tpResult, setTpResult] = useState<ThroughputResult | null>(null);
  // Noise QRAM
  const [qrCase, setQrCase] = useState("lookup");
  const [qrAddress, setQrAddress] = useState(5);
  const [qrSeed, setQrSeed] = useState(0);
  const [qrModelSeed, setQrModelSeed] = useState(42);
  const [qrResult, setQrResult] = useState<NoiseQRAMResult | null>(null);

  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  async function post<T>(kind: string, path: string, body: unknown, apply: (data: T) => void) {
    setBusy(kind);
    setError("");
    apply(null as unknown as T);
    try {
      const response = await api.post<T>(path, body);
      apply(response.data);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy("");
    }
  }

  const numberField = (label: string, value: number, set: (v: number) => void, min: number, max: number, step = 1) => (
    <label>{label}<br /><input aria-label={label} type="number" min={min} max={max} step={step} value={value}
      onChange={event => { set(Number(event.target.value)); }} disabled={!!busy} /></label>
  );

  return <section style={{ maxWidth: 1100 }}>
    <h1>Local benchmarks</h1>
    <p style={{ color: "var(--text-muted)" }}>
      Every run executes real local computation on the packaged simulator stack. No cloud task is submitted and no
      quota is consumed. Export any result as JSON for reports.
    </p>

    {error && <p role="alert" style={{ color: "var(--error)" }}>{error}</p>}

    <fieldset className="card" disabled={!!busy} style={{ display: "flex", flexWrap: "wrap", alignItems: "end", gap: 20 }}>
      <legend>Quantum Volume (Cross et al. 2019)</legend>
      {numberField("Width (QV=2^w)", qvWidth, setQvWidth, 2, 6)}
      {numberField("Trials", qvTrials, setQvTrials, 1, 100)}
      {numberField("Seed", qvSeed, setQvSeed, 0, 2147483647)}
      <button className="btn btn-primary" onClick={() =>
        post<QVResult>("qv", "/benchmarks/qv", { width: qvWidth, trials: qvTrials, shots: 1000, seed: qvSeed }, setQvResult)
      } disabled={!!busy}>{busy === "qv" ? "Running…" : "Run QV"}</button>
    </fieldset>
    {qvResult && <div style={{ display: "flex", flexWrap: "wrap", gap: 16, margin: "16px 0" }}>
      <div className="card">mean h<br /><strong>{qvResult.mean_heavy_output_probability.toFixed(4)} ± {qvResult.sigma_mean.toFixed(4)}</strong></div>
      <div className="card">trials passed<br /><strong>{qvResult.trials_passed}/{qvResult.trials}</strong></div>
      <div className="card">verdict (h−2σ &gt; 2/3)<br /><strong>{qvResult.passed ? "PASS" : "FAIL"}</strong></div>
      <div className="card">Quantum Volume<br /><strong>{qvResult.quantum_volume ?? "—"}</strong></div>
      <button className="btn btn-ghost" onClick={() => downloadJson(qvResult, `uniqc-qv-w${qvResult.width}.json`)}>Export JSON</button>
    </div>}

    <fieldset className="card" disabled={!!busy} style={{ display: "flex", flexWrap: "wrap", alignItems: "end", gap: 20, marginTop: 24 }}>
      <legend>Compile/execute throughput</legend>
      {numberField("Circuits", tpCircuits, setTpCircuits, 10, 2000)}
      {numberField("Qubits", tpQubits, setTpQubits, 2, 16)}
      {numberField("Depth", tpDepth, setTpDepth, 1, 30)}
      {numberField("Seed", tpSeed, setTpSeed, 0, 2147483647)}
      <button className="btn btn-primary" onClick={() =>
        post<ThroughputResult>("tp", "/benchmarks/throughput",
          { circuits: tpCircuits, qubits: tpQubits, depth: tpDepth, shots: 1000, seed: tpSeed }, setTpResult)
      } disabled={!!busy}>{busy === "tp" ? "Measuring…" : "Run throughput"}</button>
    </fieldset>
    {tpResult && <div style={{ display: "flex", flexWrap: "wrap", gap: 16, margin: "16px 0" }}>
      <div className="card">circuits/hour<br /><strong>{Math.round(tpResult.timing.circuits_per_hour).toLocaleString()}</strong></div>
      <div className="card">compile<br /><strong>{tpResult.timing.compile_seconds.toFixed(3)} s</strong></div>
      <div className="card">execute<br /><strong>{tpResult.timing.execute_seconds.toFixed(3)} s</strong></div>
      <div className="card">≥ 30,000/h<br /><strong>{tpResult.meets_30000_per_hour ? "PASS" : "BELOW"}</strong></div>
      <button className="btn btn-ghost" onClick={() => downloadJson(tpResult, "uniqc-throughput.json")}>Export JSON</button>
    </div>}

    <fieldset className="card" disabled={!!busy} style={{ display: "flex", flexWrap: "wrap", alignItems: "end", gap: 20, marginTop: 24 }}>
      <legend>Noisy-VM 3-layer QRAM (synthetic exchange model)</legend>
      <label>Case<br /><select aria-label="Case" value={qrCase} onChange={event => setQrCase(event.target.value)} disabled={!!busy}>
        <option value="lookup">Basis-address lookup</option>
        <option value="qpu">QPU superposition addressing</option>
      </select></label>
      {qrCase === "lookup" && numberField("Address", qrAddress, setQrAddress, 0, 7)}
      {numberField("Shot seed", qrSeed, setQrSeed, 0, 2147483647)}
      {numberField("Model seed", qrModelSeed, setQrModelSeed, 0, 2147483647)}
      <button className="btn btn-primary" onClick={() =>
        post<NoiseQRAMResult>("qr", "/benchmarks/noise-qram",
          { case: qrCase, address: qrAddress, shots: 1000, seed: qrSeed, model_seed: qrModelSeed }, setQrResult)
      } disabled={!!busy}>{busy === "qr" ? "Running…" : "Run QRAM case"}</button>
    </fieldset>
    {qrResult && <div style={{ display: "flex", flexWrap: "wrap", gap: 16, margin: "16px 0" }}>
      {qrCase === "lookup" && <>
        <div className="card">expected value<br /><strong>{qrResult.expected_value} ({qrResult.expected_value?.toString(2).padStart(2, "0")})</strong></div>
        <div className="card">raw accuracy<br /><strong>{(100 * (qrResult.raw_accuracy ?? 0)).toFixed(1)}%</strong></div>
        <div className="card">mitigated accuracy<br /><strong>{(100 * (qrResult.mitigated_accuracy ?? 0)).toFixed(1)}%</strong></div>
      </>}
      {qrCase === "qpu" && <>
        <div className="card">raw fidelity<br /><strong>{(qrResult.raw_fidelity ?? 0).toFixed(4)}</strong></div>
        <div className="card">mitigated fidelity<br /><strong>{(qrResult.mitigated_fidelity ?? 0).toFixed(4)}</strong></div>
        <div className="card">ideal distribution<br /><strong>{JSON.stringify(qrResult.ideal_distribution)}</strong></div>
      </>}
      <button className="btn btn-ghost" onClick={() => downloadJson(qrResult, `uniqc-qram-${qrCase}.json`)}>Export JSON</button>
    </div>}
    {qrResult && <div className="card" style={{ marginTop: 8 }}>
      <h2>Counts (raw → readout-mitigated)</h2>
      <div style={{ display: "grid", gridTemplateColumns: "100px 1fr 1fr 90px", gap: 12, alignItems: "center" }}>
        {Object.keys(qrResult.noisy_counts).sort().map(bits => {
          const raw = qrResult.noisy_counts[bits] ?? 0;
          const mit = qrResult.mitigated_counts[bits] ?? 0;
          const total = Object.values(qrResult.noisy_counts).reduce((a, b) => a + b, 0) || 1;
          return [<code key={`${bits}k`}>{bits}</code>,
            <div key={`${bits}r`} style={{ background: "var(--border)", borderRadius: 4, height: 14 }}><div
              style={{ background: "var(--accent)", height: "100%", borderRadius: 4, width: `${(100 * raw) / total}%` }} /></div>,
            <div key={`${bits}m`} style={{ background: "var(--border)", borderRadius: 4, height: 14 }}><div
              style={{ background: "var(--success)", height: "100%", borderRadius: 4, width: `${(100 * mit) / total}%` }} /></div>,
            <span key={`${bits}v`}>{raw} → {mit}</span>];
        })}
      </div>
      <p style={{ color: "var(--text-muted)", marginTop: 12 }}>{qrResult.boundary}</p>
    </div>}
  </section>;
}
