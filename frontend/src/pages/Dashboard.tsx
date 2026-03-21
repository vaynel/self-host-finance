import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { AppLayout } from "@/components/AppLayout";
import { StatCard } from "@/components/StatCard";
import { Card } from "@/components/ui/card";
import {
  Wallet, TrendingDown, TrendingUp, PiggyBank, ArrowUpRight, ArrowDownRight, Loader2,
  BellRing, AlertTriangle, BarChart3,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from "recharts";
import { cn } from "@/lib/utils";
import { transactionsApi, accountsApi, investmentsApi, reportsApi } from "@/lib/api";
import { useMemo } from "react";

// 카테고리 색상 팔레트
const CATEGORY_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

function toNumberSafe(value: unknown): number {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

function formatKRW(value: unknown) {
  const v = toNumberSafe(value);
  if (Math.abs(v) >= 10000) {
    return `${(v / 10000).toFixed(0)}만원`;
  }
  return `${v.toLocaleString()}원`;
}

function formatKRWFull(value: unknown) {
  const v = toNumberSafe(value);
  return `₩${v.toLocaleString()}`;
}

const TRIGGER_KIND_LABEL: Record<string, string> = {
  cost_drop: "원금 대비 하락",
  peak_drop: "고점 대비 하락",
};

export default function Dashboard() {
  // API 데이터 페칭
  const { data: transactionsData, isLoading: transactionsLoading } = useQuery({
    queryKey: ["transactions", { limit: 6 }],
    queryFn: async () => {
      const response = await transactionsApi.list({ limit: 6 });
      return response.data || [];
    },
  });

  const { data: accountsData, isLoading: accountsLoading } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => {
      const response = await accountsApi.list();
      return response.data || [];
    },
  });

  const { data: holdingsData, isLoading: holdingsLoading } = useQuery({
    queryKey: ["investments", "holdings"],
    queryFn: async () => {
      const response = await investmentsApi.getHoldings();
      return response.data || [];
    },
  });

  const { data: monthlySummaryData, isLoading: monthlySummaryLoading } = useQuery({
    queryKey: ["reports", "monthly-summary"],
    queryFn: async () => {
      const response = await reportsApi.getMonthlySummary();
      return response.data || [];
    },
  });

  const { data: categorySpendingData, isLoading: categorySpendingLoading } = useQuery({
    queryKey: ["reports", "category-spending"],
    queryFn: async () => {
      const response = await reportsApi.getCategorySpending();
      return response.data || [];
    },
  });

  const { data: ruleTriggers = [] } = useQuery({
    queryKey: ["investments", "rules", "triggers"],
    queryFn: async () => (await investmentsApi.listRuleTriggers()).data || [],
    refetchInterval: 60 * 1000,
  });

  const { data: dashTickerRules = [] } = useQuery({
    queryKey: ["investments", "rules", "ticker"],
    queryFn: async () => (await investmentsApi.listRules()).data || [],
  });

  const { data: dashGlobalRules = [] } = useQuery({
    queryKey: ["investments", "rules", "global"],
    queryFn: async () => (await investmentsApi.listGlobalRules()).data || [],
  });

  const activeRulesSummary = useMemo(() => ({
    ticker: dashTickerRules.filter((r) => r.enabled).length,
    global: dashGlobalRules.filter((r) => r.enabled).length,
  }), [dashTickerRules, dashGlobalRules]);

  const isLoading = transactionsLoading || accountsLoading || holdingsLoading || monthlySummaryLoading || categorySpendingLoading;

  // 계산된 값들
  const investmentTotal = useMemo(() => {
    if (!holdingsData) return 0;
    return holdingsData.reduce((sum, h) => sum + h.totalValue, 0);
  }, [holdingsData]);

  const investmentCostBasis = useMemo(() => {
    if (!holdingsData) return 0;
    return holdingsData.reduce((sum, h) => sum + h.avgPrice * h.shares, 0);
  }, [holdingsData]);

  const totalAssets = useMemo(() => {
    if (!accountsData) return 0;
    const accountTotal = accountsData.reduce((sum, a) => sum + (a.balance > 0 ? a.balance : 0), 0);
    return accountTotal + investmentTotal;
  }, [accountsData, investmentTotal]);

  const totalLiabilities = useMemo(() => {
    if (!accountsData) return 0;
    return accountsData.reduce((sum, a) => sum + (a.balance < 0 ? Math.abs(a.balance) : 0), 0);
  }, [accountsData]);

  const netWorth = totalAssets - totalLiabilities;

  /** 이번 달·전월 행 (월별 요약 API) */
  const monthRows = useMemo(() => {
    const now = new Date();
    const currentYm = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    const prevD = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const prevYm = `${prevD.getFullYear()}-${String(prevD.getMonth() + 1).padStart(2, "0")}`;
    const rows = monthlySummaryData || [];
    return {
      currentYm,
      prevYm,
      current: rows.find((m) => m.month === currentYm),
      prev: rows.find((m) => m.month === prevYm),
    };
  }, [monthlySummaryData]);

  const thisMonthExpense = useMemo(() => {
    return monthRows.current?.expense ?? 0;
  }, [monthRows]);

  /** 지출 전월 대비 % (월별 요약 API) */
  const expenseChangeMeta = useMemo(() => {
    const cur = monthRows.current;
    const p = monthRows.prev;
    if (!cur || !p || p.expense <= 0) return null;
    const pct = ((cur.expense - p.expense) / p.expense) * 100;
    const text = `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}% 전월 대비 지출`;
    const changeType = pct <= 0 ? "positive" as const : "negative" as const;
    return { text, changeType };
  }, [monthRows]);

  /** 보유 종목 평가·원금 기준 수익률 (holdings API) */
  const portfolioReturnPct = useMemo(() => {
    if (!holdingsData?.length || investmentCostBasis <= 0) return null;
    return ((investmentTotal - investmentCostBasis) / investmentCostBasis) * 100;
  }, [holdingsData, investmentCostBasis, investmentTotal]);

  /** 총 자산 대비 투자 비중 (계좌·보유 API) */
  const investShareOfAssetsPct = useMemo(() => {
    if (totalAssets <= 0) return null;
    return (investmentTotal / totalAssets) * 100;
  }, [totalAssets, investmentTotal]);

  // 월별 데이터 변환
  const monthlySpending = useMemo(() => {
    if (!monthlySummaryData) return [];
    return monthlySummaryData.map((m) => ({
      month: m.month.slice(5), // "2026-03" -> "03"
      income: m.income,
      expense: m.expense,
    }));
  }, [monthlySummaryData]);

  // 카테고리별 소비 (/reports/category-spending → category·amount 또는 name·value)
  const categorySpending = useMemo(() => {
    if (!categorySpendingData) return [];
    return categorySpendingData.map(
      (cat: { category?: string; name?: string; amount?: number; value?: number; color?: string }, index: number) => ({
        name: cat.category ?? cat.name ?? "기타",
        value: toNumberSafe(cat.amount ?? cat.value),
        color: cat.color || CATEGORY_COLORS[index % CATEGORY_COLORS.length],
      }),
    );
  }, [categorySpendingData]);

  const recentTransactions = useMemo(() => {
    return (transactionsData || []).slice(0, 6);
  }, [transactionsData]);

  if (isLoading) {
    return (
      <AppLayout title="대시보드">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="대시보드">
      <div className="space-y-6 max-w-7xl">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="총 자산"
            value={formatKRW(totalAssets)}
            change={
              investShareOfAssetsPct != null
                ? `투자 ${investShareOfAssetsPct.toFixed(0)}% · 유동(계좌+) ${(100 - investShareOfAssetsPct).toFixed(0)}%`
                : undefined
            }
            changeType="neutral"
            icon={Wallet}
            iconClassName="bg-accent"
          />
          <StatCard
            label="순자산"
            value={formatKRW(netWorth)}
            change={
              monthRows.current
                ? `이번 달 저축 ${formatKRW(monthRows.current.savings)} · 저축률 ${monthRows.current.savingsRate.toFixed(1)}%`
                : undefined
            }
            changeType="neutral"
            icon={PiggyBank}
            iconClassName="bg-accent"
          />
          <StatCard
            label="이번 달 소비"
            value={formatKRW(thisMonthExpense)}
            change={expenseChangeMeta?.text}
            changeType={expenseChangeMeta?.changeType ?? "neutral"}
            icon={TrendingDown}
            iconClassName="bg-destructive/10"
          />
          <StatCard
            label="투자 자산"
            value={formatKRW(investmentTotal)}
            change={
              portfolioReturnPct != null
                ? `${portfolioReturnPct >= 0 ? "+" : ""}${portfolioReturnPct.toFixed(2)}% 평가수익률`
                : holdingsData?.length
                  ? "원금 대비 계산 불가"
                  : undefined
            }
            changeType={
              portfolioReturnPct == null
                ? "neutral"
                : portfolioReturnPct >= 0
                  ? "positive"
                  : "negative"
            }
            icon={TrendingUp}
            iconClassName="bg-accent"
          />
        </div>

        {/* 투자 룰: 종목별·글로벌 트리거 (Investments와 동일 캐시 키) */}
        <Card
          className={cn(
            "glass-card",
            ruleTriggers.length > 0 && "border-destructive/35 bg-destructive/[0.06]",
          )}
        >
          <div className="p-5 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                {ruleTriggers.length > 0 ? (
                  <BellRing className="h-4 w-4 text-destructive shrink-0 animate-pulse" />
                ) : (
                  <BarChart3 className="h-4 w-4 text-muted-foreground shrink-0" />
                )}
                <h3 className="text-sm font-semibold">투자 알림·매도 룰</h3>
              </div>
              <p className="text-xs text-muted-foreground">
                활성 룰: 종목별{" "}
                <span className="font-mono text-foreground">{activeRulesSummary.ticker}</span>
                건 · 글로벌{" "}
                <span className="font-mono text-foreground">{activeRulesSummary.global}</span>
                건
              </p>
            </div>
            <Link
              to="/investments"
              className="text-xs font-medium text-primary hover:underline shrink-0"
            >
              투자 관리에서 설정 →
            </Link>
          </div>
          {ruleTriggers.length === 0 ? (
            <div className="px-5 pb-5 text-sm text-muted-foreground border-t border-border pt-3">
              현재 조건을 만족하는 트리거가 없습니다.
            </div>
          ) : (
            <div className="px-5 pb-5 space-y-2 border-t border-border pt-3">
              {(ruleTriggers as Array<{
                rule: { id: string; trigger_kind: string; trigger_percent: number };
                name: string;
                ticker: string;
                actual: number;
              }>).map((item, i) => (
                <div
                  key={`${item.rule.id}-${item.ticker}-${i}`}
                  className="flex items-center justify-between gap-2 text-xs bg-background/60 rounded-lg px-3 py-2 border border-border"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <AlertTriangle className="h-3.5 w-3.5 text-destructive shrink-0" />
                    <span className="font-medium truncate">{item.name}</span>
                    <span className="text-muted-foreground truncate hidden sm:inline">
                      {TRIGGER_KIND_LABEL[item.rule.trigger_kind] ?? item.rule.trigger_kind}{" "}
                      {item.rule.trigger_percent}%
                    </span>
                  </div>
                  <span className="font-mono text-destructive font-semibold shrink-0">
                    -{Number(item.actual).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Monthly Spending Chart */}
          <Card className="p-5 glass-card lg:col-span-2">
            <h3 className="text-sm font-semibold mb-4">월별 수입/지출</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={monthlySpending} barGap={4}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    stroke="hsl(var(--muted-foreground))"
                    tickFormatter={(v) => `${(v / 10000).toFixed(0)}만`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                    formatter={(value: number) => [formatKRWFull(value)]}
                  />
                  <Bar dataKey="income" name="수입" fill="hsl(var(--chart-income))" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                  <Bar dataKey="expense" name="지출" fill="hsl(var(--chart-expense))" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Category Pie Chart */}
          <Card className="p-5 glass-card">
            <h3 className="text-sm font-semibold mb-4">카테고리별 소비</h3>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categorySpending.slice(0, 5)}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                    isAnimationActive={false}
                  >
                    {categorySpending.slice(0, 5).map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.color}
                        stroke="hsl(var(--border))"
                        strokeWidth={1.5}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                      color: "hsl(var(--card-foreground))",
                    }}
                    formatter={(value: number) => [formatKRWFull(value)]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-1.5 mt-2">
              {categorySpending.slice(0, 5).map((cat, index) => (
                <div key={`${cat.name || "category"}-${index}`} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: cat.color, boxShadow: "0 0 0 2px hsl(var(--card))" }}
                    />
                    <span className="text-foreground/80">{cat.name}</span>
                  </div>
                  <span className="font-mono font-medium text-foreground">{formatKRW(cat.value)}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Recent Transactions */}
        <Card className="glass-card">
          <div className="p-5 pb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold">최근 거래</h3>
            <a href="/transactions" className="text-xs text-primary hover:underline">전체보기</a>
          </div>
          <div className="divide-y divide-border">
            {recentTransactions.length === 0 ? (
              <div className="p-12 text-center text-muted-foreground text-sm">
                거래 내역이 없습니다
              </div>
            ) : (
              recentTransactions.map((tx) => (
                <div key={tx.id} className="px-5 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "h-8 w-8 rounded-lg flex items-center justify-center",
                    tx.amount > 0 ? "bg-accent" : "bg-destructive/10"
                  )}>
                    {tx.amount > 0 ? (
                      <ArrowUpRight className="h-4 w-4 text-income" />
                    ) : (
                      <ArrowDownRight className="h-4 w-4 text-expense" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium">{tx.description}</p>
                    <p className="text-xs text-muted-foreground">{tx.category} · {tx.account}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={cn(
                    "text-sm font-mono font-semibold",
                    tx.amount > 0 ? "text-income" : "text-foreground"
                  )}>
                    {tx.amount > 0 ? "+" : ""}{formatKRWFull(tx.amount)}
                  </p>
                  <p className="text-[10px] text-muted-foreground">{tx.date}</p>
                </div>
              </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
