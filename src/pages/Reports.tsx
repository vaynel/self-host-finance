import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { monthlySpending, categorySpending } from "@/data/mockData";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell,
} from "recharts";

function formatKRW(value: number) {
  return `₩${value.toLocaleString()}`;
}

const savingsData = monthlySpending.map((m) => ({
  ...m,
  savings: m.income - m.expense,
  savingsRate: Math.round(((m.income - m.expense) / m.income) * 100),
}));

const assetTrend = [
  { month: "10월", assets: 32000000 },
  { month: "11월", assets: 33500000 },
  { month: "12월", assets: 34200000 },
  { month: "1월", assets: 35100000 },
  { month: "2월", assets: 35800000 },
  { month: "3월", assets: 36300000 },
];

export default function Reports() {
  return (
    <AppLayout title="리포트">
      <div className="space-y-6 max-w-6xl">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Monthly Income vs Expense */}
          <Card className="p-5 glass-card">
            <h3 className="text-sm font-semibold mb-4">월별 수입 vs 지출</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={monthlySpending}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                  <YAxis tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" tickFormatter={(v) => `${(v / 10000).toFixed(0)}만`} />
                  <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} formatter={(v: number) => [formatKRW(v)]} />
                  <Bar dataKey="income" name="수입" fill="hsl(var(--chart-income))" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="expense" name="지출" fill="hsl(var(--chart-expense))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Savings Rate */}
          <Card className="p-5 glass-card">
            <h3 className="text-sm font-semibold mb-4">저축률 추이</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={savingsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                  <YAxis tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" tickFormatter={(v) => `${v}%`} />
                  <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} formatter={(v: number) => [`${v}%`]} />
                  <Line type="monotone" dataKey="savingsRate" name="저축률" stroke="hsl(var(--chart-income))" strokeWidth={2.5} dot={{ fill: "hsl(var(--chart-income))", r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Category Breakdown */}
          <Card className="p-5 glass-card">
            <h3 className="text-sm font-semibold mb-4">카테고리별 소비</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={categorySpending} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={2} dataKey="value">
                    {categorySpending.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} formatter={(v: number) => [formatKRW(v)]} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-1.5 mt-2">
              {categorySpending.map((cat) => (
                <div key={cat.name} className="flex items-center gap-2 text-xs">
                  <div className="h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: cat.color }} />
                  <span className="text-muted-foreground truncate">{cat.name}</span>
                  <span className="font-mono ml-auto">{formatKRW(cat.value)}</span>
                </div>
              ))}
            </div>
          </Card>

          {/* Asset Trend */}
          <Card className="p-5 glass-card">
            <h3 className="text-sm font-semibold mb-4">자산 변화 추이</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={assetTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                  <YAxis tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" tickFormatter={(v) => `${(v / 10000).toFixed(0)}만`} />
                  <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} formatter={(v: number) => [formatKRW(v)]} />
                  <Line type="monotone" dataKey="assets" name="총 자산" stroke="hsl(var(--chart-investment))" strokeWidth={2.5} dot={{ fill: "hsl(var(--chart-investment))", r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}
