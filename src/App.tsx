import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import type { Dataset, Recommendation, SearchResponse, Source } from "./types";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const SOURCES: Source[] = ["Hugging Face", "Kaggle", "UCI"];
const SCORE_WEIGHTS: Record<string, number> = {
  task_relevance: 30,
  semantic_similarity: 25,
  feature_compatibility: 20,
  domain_relevance: 15,
  metadata_completeness: 10,
};

function App() {
  const [description, setDescription] = useState("");
  const [selectedSources, setSelectedSources] = useState<Source[]>(SOURCES);
  const [results, setResults] = useState<Recommendation[]>([]);
  const [providers, setProviders] = useState<Record<string, string>>({});
  const [checked, setChecked] = useState<string[]>([]);
  const [filters, setFilters] = useState<Record<string, string[]>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function search(event: FormEvent) {
    event.preventDefault();
    if (description.trim().length < 3) {
      setError("Describe your machine learning task in a little more detail.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API}/api/datasets/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description, sources: selectedSources, limit_per_source: 10 }),
      });
      if (!response.ok) throw new Error((await response.json()).detail ?? "Dataset search failed.");
      const data: SearchResponse = await response.json();
      setResults(data.results);
      setProviders(data.providers);
      setFilters({});
      setChecked([]);
    } catch (reason) {
      setResults([]);
      setError(reason instanceof Error ? reason.message : "Could not connect to the dataset service.");
    } finally {
      setLoading(false);
    }
  }

  const filtered = useMemo(
    () => results.filter(({ dataset }) => Object.entries(filters).every(([key, values]) => {
      if (!values.length) return true;
      const actual = key === "source" ? [dataset.source]
        : key === "task" ? dataset.task_types
        : key === "domain" ? [dataset.domain ?? ""]
        : key === "data_type" ? [dataset.data_type ?? ""]
        : key === "license" ? [dataset.license ?? ""]
        : [dataset.download_url || dataset.source === "Kaggle" ? "download" : "view"];
      return actual.some((value) => values.includes(value));
    })),
    [results, filters],
  );
  const selected: Recommendation[] = results
    .filter(({ dataset }) => checked.includes(dataset.id))
    .slice(0, 5)

  function toggleSource(source: Source) {
    setSelectedSources((current) =>
      current.includes(source) ? current.filter((value) => value !== source) : [...current, source],
    );
  }

  async function download(dataset: Dataset) {
    try {
      const response = await fetch(
        `${API}/api/datasets/${encodeURIComponent(dataset.id)}/download`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(dataset) },
      );
      if (!response.ok) {
        const detail = (await response.json()).detail;
        throw new Error(detail ?? "Download failed.");
      }
      const link = document.createElement("a");
      link.href = URL.createObjectURL(await response.blob());
      link.download = `${dataset.id.replace(":", "-")}.zip`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Download failed.");
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="#" aria-label="Dataset Negotiator home">
          <span className="brand-mark">D</span> dataset<span>negotiator</span>
        </a>
        <a className="github-link" href="https://github.com/" target="_blank" rel="noreferrer">Dataset discovery workspace</a>
      </header>

      <section className="hero">
        <div className="eyebrow"><span className="pulse" /> INTELLIGENT DATASET DISCOVERY</div>
        <h1>Find the right data<br /><span>for what you’re building.</span></h1>
        <p>Describe your ML task. Compare real datasets from trusted repositories.</p>
        <form className="search-panel" onSubmit={search}>
          <label htmlFor="task">What are you trying to solve?</label>
          <textarea
            id="task"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="e.g. I need a dataset for predicting house prices using regression"
            rows={3}
            maxLength={2000}
          />
          <div className="search-bottom">
            <div className="source-list" aria-label="Dataset sources">
              {SOURCES.map((source) => (
                <label key={source} className="source-option">
                  <input type="checkbox" checked={selectedSources.includes(source)} onChange={() => toggleSource(source)} />
                  {source}
                </label>
              ))}
            </div>
            <button type="submit" className="primary-button" disabled={loading || selectedSources.length === 0}>
              {loading ? "Searching…" : "Find datasets"} <span aria-hidden="true">→</span>
            </button>
          </div>
        </form>
        {error && <p className="error" role="alert">{error}</p>}
      </section>

      {(Object.keys(providers).length > 0) && (
        <section className="provider-status" aria-label="Provider status">
          {Object.entries(providers).map(([source, status]) => (
            <span key={source} className={status.startsWith("ok") ? "status-ok" : "status-warn"}>
              <i /> {source}: {status}
            </span>
          ))}
        </section>
      )}

      {results.length > 0 && (
        <>
          <section className="results-heading">
            <div><div className="eyebrow">YOUR MATCHES</div><h2>Recommended datasets <span className="count">{filtered.length}</span></h2></div>
            <div className="filter-controls">
              <FilterSelect label="Source" filterKey="source" values={results.map(({ dataset }) => dataset.source)} filters={filters} setFilters={setFilters} />
              <FilterSelect label="Task" filterKey="task" values={results.flatMap(({ dataset }) => dataset.task_types)} filters={filters} setFilters={setFilters} />
              <FilterSelect label="Domain" filterKey="domain" values={results.map(({ dataset }) => dataset.domain).filter((value): value is string => Boolean(value))} filters={filters} setFilters={setFilters} />
              <FilterSelect label="Format" filterKey="data_type" values={results.map(({ dataset }) => dataset.data_type).filter((value): value is string => Boolean(value))} filters={filters} setFilters={setFilters} />
              <FilterSelect label="License" filterKey="license" values={results.map(({ dataset }) => dataset.license).filter((value): value is string => Boolean(value))} filters={filters} setFilters={setFilters} />
              <FilterSelect label="Availability" filterKey="availability" values={results.map(({ dataset }) => dataset.download_url || dataset.source === "Kaggle" ? "download" : "view")} filters={filters} setFilters={setFilters} />
            </div>
          </section>
          <div className="results-grid">
            {filtered.map((item) => (
              <DatasetCard
                key={item.dataset.id}
                item={item}
                checked={checked.includes(item.dataset.id)}
                compareDisabled={!checked.includes(item.dataset.id) && checked.length >= 5}
                onCompare={(id) => setChecked((current) => current.includes(id) ? current.filter((value) => value !== id) : current.length < 5 ? [...current, id] : current)}
                onDownload={download}
              />
            ))}
          </div>
          {selected.length > 0 && <Comparison recommendations={selected} />}
          {filtered.length === 0 && <p className="empty-state">No datasets match this source filter.</p>}
        </>
      )}

      {!loading && Object.keys(providers).length > 0 && results.length === 0 && (
        <p className="empty-state">No matching datasets were returned. Try different task words or another source.</p>
      )}
      <footer>Scores are based on available repository metadata. Dataset contents are not downloaded or inspected during recommendations.</footer>
    </main>
  );
}

function DatasetCard({ item, checked, compareDisabled, onCompare, onDownload }: {
  item: Recommendation; checked: boolean; compareDisabled: boolean;
  onCompare: (id: string) => void; onDownload: (dataset: Dataset) => void;
}) {
  const { dataset } = item;
  return (
    <article className="dataset-card">
      <div className="card-top">
        <span className={`source-badge ${dataset.source.toLowerCase().replace(" ", "-")}`}>{dataset.source}</span>
        <div className="score"><strong>{Math.round(item.score)}</strong><span>/ 100</span></div>
      </div>
      <h3>{dataset.name}</h3>
      <p className="description">{dataset.description || "No description provided by the dataset source."}</p>
      <div className="tag-row">
        {(dataset.task_types.length ? dataset.task_types : [item.compatibility.status + " match"]).slice(0, 3).map((tag) => <span className="tag" key={tag}>{tag}</span>)}
        {dataset.data_type && <span className="tag muted">{dataset.data_type}</span>}
      </div>
      <div className="quality">
        <div className="quality-head"><span>Metadata quality</span><strong>{item.quality.score}%</strong></div>
        <div className="progress"><span style={{ width: `${item.quality.score}%` }} /></div>
        <span className="compatibility">{item.compatibility.status} compatibility · {item.quality.assessment}</span>
        <div className="indicators">{Object.entries(item.quality.indicators).filter(([, present]) => present).map(([name]) => name.replace(/_/g, " ")).join(" · ") || "No quality metadata verified"}</div>
      </div>
      <p className="explanation">{item.explanation}</p>
      <details className="score-details">
        <summary>How the score was calculated</summary>
        {Object.entries(item.factors).map(([factor, value]) => {
          const label = factor.replace(/_/g, " ");
          const weight = SCORE_WEIGHTS[factor] ?? 0;
          return <span key={factor}>{label} ({weight}%) <b>{Math.round(value)}%</b></span>;
        })}
      </details>
      <div className="metadata">
        <span>License <b>{dataset.license || "Not available"}</b></span>
        <span>Rows <b>{dataset.rows?.toLocaleString() ?? "Not available"}</b></span>
      </div>
      {item.quality.limitations.length > 0 && <p className="limitations">Missing: {item.quality.limitations.slice(0, 3).join(", ")}</p>}
      <div className="card-actions">
        <a className="secondary-button" href={dataset.url} target="_blank" rel="noreferrer">View dataset ↗</a>
        {dataset.download_url || dataset.source === "Kaggle"
          ? <button className="secondary-button" onClick={() => onDownload(dataset)}>Download</button>
          : <span className="unavailable">Download unavailable</span>}
        <label className="compare-check">
          <input type="checkbox" checked={checked} onChange={() => onCompare(dataset.id)} disabled={compareDisabled} />
          Compare
        </label>
      </div>
    </article>
  );
}

function FilterSelect({ label, filterKey, values, filters, setFilters }: {
  label: string;
  filterKey: string;
  values: string[];
  filters: Record<string, string[]>;
  setFilters: (value: Record<string, string[]>) => void;
}) {
  const options = [...new Set(values)].sort();
  if (!options.length) return null;
  return (
    <label className="filter-control">{label}
      <select value={filters[filterKey]?.[0] ?? ""} onChange={(event) => setFilters({ ...filters, [filterKey]: event.target.value ? [event.target.value] : [] })}>
        <option value="">All</option>
        {options.map((option) => <option value={option} key={option}>{option}</option>)}
      </select>
    </label>
  );
}

function Comparison({ recommendations }: { recommendations: Recommendation[] }) {
  const datasets = recommendations.map(({ dataset }) => dataset);
  const columns: [string, (dataset: Dataset) => string][] = [
    ["Source", (dataset) => dataset.source],
    ["Description", (dataset) => dataset.description || "Not available"],
    ["Task", (dataset) => dataset.task_types.join(", ") || "Not available"],
    ["Rows", (dataset) => dataset.rows?.toLocaleString() ?? "Not available"],
    ["Size", (dataset) => dataset.size_bytes ? `${(dataset.size_bytes / 1_000_000).toFixed(1)} MB` : "Not available"],
    ["Features", (dataset) => dataset.features.join(", ") || "Not available"],
    ["License", (dataset) => dataset.license || "Not available"],
  ];
  return (
    <section className="comparison">
      <div className="eyebrow">SIDE BY SIDE</div><h2>Compare datasets <span className="count">{datasets.length}/5</span></h2>
      <div className="table-scroll"><table><thead><tr><th>Dataset</th>{datasets.map((dataset) => <th key={dataset.id}><a href={dataset.url} target="_blank" rel="noreferrer">{dataset.name}</a></th>)}</tr></thead>
        <tbody><tr><th>Recommendation</th>{recommendations.map((item) => <td key={item.dataset.id}>{Math.round(item.score)}/100</td>)}</tr>
          <tr><th>Compatibility</th>{recommendations.map((item) => <td key={item.dataset.id}>{item.compatibility.status}</td>)}</tr>
          <tr><th>Quality</th>{recommendations.map((item) => <td key={item.dataset.id}>{item.quality.score}/100 · {item.quality.assessment}</td>)}</tr>
          {columns.map(([label, value]) => <tr key={label}><th>{label}</th>{datasets.map((dataset) => <td key={dataset.id}>{value(dataset)}</td>)}</tr>)}</tbody>
      </table></div>
    </section>
  );
}

export default App;
