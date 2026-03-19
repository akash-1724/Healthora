import { Search, Bell, User } from "lucide-react";

export default function Header({ query, setQuery, onSearch, loading }) {
  return (
    <div>
      {/* Top navbar */}
      <div className="flex justify-between items-center px-6 py-3 bg-white border-b border-gray-200">
        <div>
          <h1 className="text-xl font-bold text-gray-800">Reports & Charts</h1>
          <p className="text-sm text-gray-500">
            Management reports, analytics, charts, and natural language search
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Search size={20} className="text-gray-500" />
          <div className="relative">
            <Bell size={20} className="text-gray-500" />
            <span className="absolute -top-1.5 -right-1.5 bg-red-500 text-white rounded-full w-4 h-4 text-xs flex items-center justify-center">
              3
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="text-right">
              <div className="font-semibold text-sm text-gray-800">Dr. Admin</div>
              <div className="text-xs text-gray-500">Administrator</div>
            </div>
            <div className="w-9 h-9 rounded-full bg-gray-200 flex items-center justify-center">
              <User size={18} className="text-gray-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Search section */}
      <div className="bg-teal-400 p-6">
        <div className="bg-teal-400 border-2 border-gray-800 rounded-lg p-5">
          <div className="flex items-center gap-2 mb-1">
            <Search size={18} />
            <span className="font-bold text-base">Search Records</span>
          </div>
          <p className="text-sm text-teal-900 mb-3">
            Search for medicine dispense details, doctor info, or staff records.
            Try: "paracetamol", "Dr. Sarah", "pharmacist"
          </p>
          <div className="flex gap-2">
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && onSearch()}
              placeholder="e.g. How many Amoxicillin were dispensed? / Details of Dr. Patel / Staff on duty..."
              className="flex-1 px-4 py-3 text-sm border-2 border-gray-800 rounded-lg outline-none bg-white"
            />
            <button
              onClick={onSearch}
              disabled={loading}
              className="px-6 py-3 bg-white border-2 border-gray-800 rounded-lg font-semibold text-sm flex items-center gap-2 hover:bg-gray-50 cursor-pointer disabled:opacity-50"
            >
              <Search size={16} />
              {loading ? "Searching..." : "Search"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}