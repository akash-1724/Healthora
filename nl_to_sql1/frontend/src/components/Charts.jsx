import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, Legend, ResponsiveContainer
} from "recharts";

const COLORS = ["#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE"];

function isNumeric(val) {
  return val !== null && val !== "" && !isNaN(Number(val));
}

export default function Charts({ columns, rows }) {
  if (!rows || rows.length < 2) return null;

  const labelColIdx = columns.findIndex((_, i) => !isNumeric(rows[0][i]));
  const valueColIdx = columns.findIndex((_, i) => isNumeric(rows[0][i]));

  if (labelColIdx === -1 || valueColIdx === -1) return null;

  const chartData = rows.slice(0, 15).map(row => ({
    name: String(row[labelColIdx]).length > 15
      ? String(row[labelColIdx]).slice(0, 15) + "..."
      : String(row[labelColIdx]),
    value: Number(row[valueColIdx])
  }));

  const labelCol = columns[labelColIdx];
  const valueCol = columns[valueColIdx];

  return (
    <div className="grid grid-cols-2 gap-4 px-6 pb-4">
      {/* Bar Chart */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">
          {valueCol} by {labelCol}
        </h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11 }}
              angle={-35}
              textAnchor="end"
              interval={0}
            />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="value" fill="#4ECDC4" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Pie Chart */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">
          Distribution of {valueCol}
        </h3>
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={90}
              label={({ name, percent }) =>
                `${name} ${(percent * 100).toFixed(0)}%`
              }
              labelLine={false}
            >
              {chartData.map((_, index) => (
                <Cell key={index} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}