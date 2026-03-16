import { useQuery } from "@tanstack/react-query";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Loader2 } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell,
} from "recharts";
import { reportsApi, accountsApi, investmentsApi } from "@/lib/api";
import { useMemo } from "react";

const CATEGORY_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

function formatKRW(value: number) {
  return `₩${value.toLocaleString()}`;
}

export default function Reports() {
  const { data: monthlySummaryData, isLoading: monthlyLoading } = useQuery({
    queryKey: ["reports", "monthly-summary"],
    queryFn: async () => {
      const response = await reportsApi.getMonthlySummary();
      return response.data || [];
    },
  });

  const { data: categorySpendingData, isLoading: categoryLoading } = useQuery({
    queryKey: ["reports", "category-spending"],
    queryFn: async () => {
      const response = await reportsApi.getCategorySpending();
      return response.data || [];
    },
  });

  const { data: accountsData } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => {
      const response = await accountsApi.list();
      return response.data || [];
    },
  });

  const { data: holdingsData } = useQuery({
    queryKey: ["investments", "holdings"],
    queryFn: async () => {
      const response = await investmentsApi.getHoldings();
      return response.data || [];
    },
  });

  const isLoading = monthlyLoading || categoryLoading;

  const monthlySpending = useMemo(() => {
    if (!monthlySummaryData) return [];
    return monthlySummaryData.map((m) => ({
      month: m.month.slice(5), // "2026-03" -> "03"
      income: m.income,
      expense: m.expense,
    }));
  }, [monthlySummaryData]);

  const savingsData = useMemo(() => {
    if (!monthlySummaryData) return [];
    return monthlySummaryData.map((m) => ({
      month: m.month.slice(5),
      savings: m.savings,
      savingsRate: m.savingsRate,
    }));
  }, [monthlySummaryData]);

  const categorySpending = useMemo(() => {
    if (!categorySpendingData) return [];
    return categorySpendingData.map((cat: { category?: string; name?: string; amount?: number; value?: number }, index: number) => ({
      name: cat.category ?? cat.name ?? "기타",
      value: cat.amount ?? cat.value ?? 0,
      color: CATEGORY_COLORS[index % CATEGORY_COLORS.length],
    }));
  }, [categorySpendingData]);

  const assetTrend = useMemo(() => {
    if (!monthlySummaryData || !accountsData || !holdingsData) return [];
    const investmentTotal = holdingsData.reduce((sum, h) => sum + h.totalValue, 0);
    return monthlySummaryData.map((m) => {
      // 간단한 추정: 계좌 잔액 + 투자 자산
      const accountTotal = accountsData.reduce((sum, a) => sum + (a.balance > 0 ? a.balance : 0), 0);
      return {
        month: m.month.slice(5),
        assets: accountTotal + investmentTotal,
      };
    });
  }, [monthlySummaryData, accountsData, holdingsData]);

  if (isLoading) {
    return (
      <AppLayout title="리포트">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }
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
                  <Bar dataKey="income" name="수입" fill="hsl(var(--chart-income))" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                  <Bar dataKey="expense" name="지출" fill="hsl(var(--chart-expense))" radius={[4, 4, 0, 0]} isAnimationActive={false} />
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
                  <Line type="monotone" dataKey="savingsRate" name="저축률" stroke="hsl(var(--chart-income))" strokeWidth={2.5} dot={{ fill: "hsl(var(--chart-income))", r: 4 }} isAnimationActive={false} />
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
                  <Pie data={categorySpending} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={2} dataKey="value" isAnimationActive={false}>
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
                  <Line type="monotone" dataKey="assets" name="총 자산" stroke="hsl(var(--chart-investment))" strokeWidth={2.5} dot={{ fill: "hsl(var(--chart-investment))", r: 4 }} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}
