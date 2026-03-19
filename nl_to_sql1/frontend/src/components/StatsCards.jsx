import { Edit, BarChart2, Users, TrendingDown } from "lucide-react";

const stats = [
  {
    label: "TOTAL DISPENSED",
    value: "9,200",
    change: "+14% vs last month",
    up: true,
    icon: Edit,
    bg: "bg-teal-400",
  },
  {
    label: "UNIQUE MEDICINES",
    value: "342",
    change: "+6 vs last month",
    up: true,
    icon: BarChart2,
    bg: "bg-yellow-100",
  },
  {
    label: "PATIENTS SERVED",
    value: "710",
    change: "+8% vs last month",
    up: true,
    icon: Users,
    bg: "bg-green-100",
  },
  {
    label: "AVG. PER PATIENT",
    value: "12.9",
    change: "-2% vs last month",
    up: false,
    icon: TrendingDown,
    bg: "bg-red-50",
  },
];

export default function StatsCards() {
  return (
    <div className="grid grid-cols-4 gap-4 px-6 py-4">
      {stats.map(({ label, value, change, up, icon: Icon, bg }) => (
        <div
          key={label}
          className={`${bg} rounded-xl p-4 border border-gray-200 flex flex-col gap-3`}
        >
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-gray-600 tracking-wide">
              {label}
            </span>
            <div className="w-8 h-8 bg-white bg-opacity-60 rounded-lg flex items-center justify-center">
              <Icon size={16} className="text-gray-600" />
            </div>
          </div>
          <div className="text-3xl font-bold text-gray-800">{value}</div>
          <div className={`text-xs font-medium ${up ? "text-green-700" : "text-red-600"}`}>
            {up ? "↗" : "↘"} {change}
          </div>
        </div>
      ))}
    </div>
  );
}