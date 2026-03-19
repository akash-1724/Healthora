import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import StatsCards from "./components/StatsCards";
import Charts from "./components/Charts";
import ResultsTable from "./components/ResultsTable";
import "./App.css";

const API_URL = "http://localhost:8000";

export default function App() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);

  async function onSearch() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setSearched(true);

    try {
      const response = await fetch(`${API_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Something went wrong");
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen bg-gray-100">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <div className="flex flex-col flex-1 ml-56">
        {/* Header + Search */}
        <Header
          query={query}
          setQuery={setQuery}
          onSearch={onSearch}
          loading={loading}
        />

        {/* Stats Cards — always visible */}
        {!searched && <StatsCards />}

        {/* Error */}
        {error && (
          <div className="mx-6 mt-4 p-4 bg-red-50 border border-red-300 rounded-lg text-red-700 text-sm">
            ❌ {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-16 text-gray-400">
            <div className="text-4xl mb-3">⏳</div>
            <div className="text-sm">Searching database...</div>
          </div>
        )}

        {/* Results */}
        {result && (
          <>
            {/* Status bar */}
            <div className="flex items-center gap-3 px-6 py-3 bg-white border-b border-gray-200">
              <span className="px-3 py-1 bg-teal-400 text-white rounded-full text-xs font-semibold">
                ✅ {result.count} rows found
              </span>
              {result.cached && (
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold">
                  ⚡ Cached (RAG)
                </span>
              )}
            </div>

            {/* Charts */}
            <div className="pt-4">
              <Charts columns={result.columns} rows={result.rows} />
            </div>

            {/* Table */}
            <ResultsTable
              columns={result.columns}
              rows={result.rows}
              count={result.count}
              sql={result.sql}
            />
          </>
        )}

        {/* Empty state */}
        {!searched && (
          <div className="flex flex-col items-center justify-center py-16 text-gray-400">
            <div className="text-5xl mb-4">🔍</div>
            <div className="text-base">Ask anything about the hospital database</div>
            <div className="text-sm mt-2">
              Try: "show me drugs prescribed to a patient"
            </div>
          </div>
        )}
      </div>
    </div>
  );
}