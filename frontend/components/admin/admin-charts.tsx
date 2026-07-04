"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatINR } from "@/lib/utils";

const CHART_COLORS = ["#4f9d69", "#d88c4a", "#6f8fd8", "#c66b8f", "#c7a349", "#55a9a3"];

type Row = Record<string, string | number>;

function ChartShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <h2 className="mb-4 font-heading text-lg font-semibold">{title}</h2>
      <div className="h-[320px] w-full">{children}</div>
    </section>
  );
}

export function AdminLineChart({
  title,
  rows,
  xKey,
  yKey,
  money,
}: {
  title: string;
  rows: Row[];
  xKey: string;
  yKey: string;
  money?: boolean;
}) {
  return (
    <ChartShell title={title}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows}>
          <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
          <XAxis dataKey={xKey} tick={{ fill: "#cdbab4", fontSize: 12 }} />
          <YAxis tick={{ fill: "#cdbab4", fontSize: 12 }} />
          <Tooltip
            formatter={(value) => (money ? formatINR(Number(value)) : value)}
            contentStyle={{ background: "#242124", border: "1px solid #3a3438" }}
          />
          <Line
            type="monotone"
            dataKey={yKey}
            stroke="#4f9d69"
            strokeWidth={3}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}

export function AdminBarChart({
  title,
  rows,
  xKey,
  yKey,
  money,
}: {
  title: string;
  rows: Row[];
  xKey: string;
  yKey: string;
  money?: boolean;
}) {
  return (
    <ChartShell title={title}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows}>
          <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
          <XAxis dataKey={xKey} tick={{ fill: "#cdbab4", fontSize: 12 }} />
          <YAxis tick={{ fill: "#cdbab4", fontSize: 12 }} />
          <Tooltip
            formatter={(value) => (money ? formatINR(Number(value)) : value)}
            contentStyle={{ background: "#242124", border: "1px solid #3a3438" }}
          />
          <Bar dataKey={yKey} radius={[4, 4, 0, 0]}>
            {rows.map((_, index) => (
              <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}

export function AdminPieChart({
  title,
  rows,
  nameKey,
  valueKey,
  money,
}: {
  title: string;
  rows: Row[];
  nameKey: string;
  valueKey: string;
  money?: boolean;
}) {
  return (
    <ChartShell title={title}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Tooltip
            formatter={(value) => (money ? formatINR(Number(value)) : value)}
            contentStyle={{ background: "#242124", border: "1px solid #3a3438" }}
          />
          <Pie
            data={rows}
            dataKey={valueKey}
            nameKey={nameKey}
            innerRadius={60}
            outerRadius={110}
            paddingAngle={2}
            label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
          >
            {rows.map((_, index) => (
              <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </ChartShell>
  );
}
