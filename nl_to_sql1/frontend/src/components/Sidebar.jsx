import { LayoutDashboard, BarChart2, Bell, Package, Users, Settings } from "lucide-react";

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard" },
  { icon: BarChart2, label: "Reports & Charts", active: true },
  { icon: Bell, label: "Alerts Display" },
  { icon: Package, label: "Inventory" },
  { icon: Users, label: "Staff" },
  { icon: Settings, label: "Settings" },
];

export default function Sidebar() {
  return (
    <div className="flex flex-col w-56 min-h-screen bg-white border-r border-gray-200 fixed left-0 top-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-gray-200">
        <div className="w-10 h-10 bg-teal-500 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-sm">H</span>
        </div>
        <div>
          <div className="font-bold text-gray-800 text-sm">HEALTHORA</div>
          <div className="text-xs text-gray-500">Pharmacy System</div>
        </div>
      </div>

      {/* Nav Items */}
      <nav className="flex flex-col gap-1 p-3 flex-1">
        {navItems.map(({ icon: Icon, label, active }) => (
          <button
            key={label}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors w-full text-left
              ${active
                ? "bg-teal-500 text-white"
                : "text-gray-600 hover:bg-gray-100"
              }`}
          >
            <Icon size={18} />
            {label}
          </button>
        ))}
      </nav>
    </div>
  );
}