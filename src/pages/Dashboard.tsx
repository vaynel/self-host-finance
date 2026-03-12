import { AppLayout } from "@/components/AppLayout";
import { StatCard } from "@/components/StatCard";
import { Card } from "@/components/ui/card";
import { Wallet, TrendingDown, TrendingUp, PiggyBank, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { transactions, monthlySpending, categorySpending, accounts, investmentTrades, dailyPrices } from "@/data/mockData";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from "recharts";
import { cn } from "@/lib/utils";

// 거래 기록에서 보유 종목 계산
function computeInvestmentTotal() {
  const map = new Map<string, { shares: number; ticker: string }>();
  for (const t of investmentTrades) {
    const cur = map.get(t.ticker) || { shares: 0, ticker: t.ticker };
    cur.shares += t.action === "buy" ? t.shares : -t.shares;
    map.set(t.ticker, cur);
  }
  let total = 0;
  for (const [ticker, v] of map) {
    if (v.shares <= 0) continue;
    const prices = dailyPrices.filter((p) => p.ticker === ticker);
    const latest = prices.length > 0 ? prices[prices.length - 1].close : 0;
    total += latest * v.shares;
  }
  return total;
}

const investmentTotal = computeInvestmentTotal();
const totalAssets = accounts.reduce((sum, a) => sum + (a.balance > 0 ? a.balance : 0), 0) + investmentTotal;

const totalLiabilities = accounts.reduce((sum, a) => sum + (a.balance < 0 ? Math.abs(a.balance) : 0), 0);
const netWorth = totalAssets - totalLiabilities;

const thisMonthExpense = 1470700;

function formatKRW(value: number) {
  if (Math.abs(value) >= 10000) {
    return `${(value / 10000).toFixed(0)}만원`;
  }
  return `${value.toLocaleString()}원`;
}

function formatKRWFull(value: number) {
  return `₩${value.toLocaleString()}`;
}

export default function Dashboard() {
  const recentTransactions = transactions.slice(0, 6);

  return (
    <AppLayout title="대시보드">
      <div className="space-y-6 max-w-7xl">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="총 자산"
            value={formatKRW(totalAssets)}
            change="+2.3% 전월 대비"
            changeType="positive"
            icon={Wallet}
            iconClassName="bg-accent"
          />
          <StatCard
            label="순자산"
            value={formatKRW(netWorth)}
            change="+1.8% 전월 대비"
            changeType="positive"
            icon={PiggyBank}
            iconClassName="bg-accent"
          />
          <StatCard
            label="이번 달 소비"
            value={formatKRW(thisMonthExpense)}
            change="-12% 전월 대비"
            changeType="positive"
            icon={TrendingDown}
            iconClassName="bg-destructive/10"
          />
          <StatCard
            label="투자 자산"
            value={formatKRW(investmentTotal)}
            change="+5.2% 수익률"
            changeType="positive"
            icon={TrendingUp}
            iconClassName="bg-accent"
          />
        </div>

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
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                    formatter={(value: number) => [formatKRWFull(value)]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-1.5 mt-2">
              {categorySpending.slice(0, 5).map((cat) => (
                <div key={cat.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: cat.color }} />
                    <span className="text-muted-foreground">{cat.name}</span>
                  </div>
                  <span className="font-mono font-medium">{formatKRW(cat.value)}</span>
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
            {recentTransactions.map((tx) => (
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
            ))}
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
