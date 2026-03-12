import { useState, useMemo } from "react";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { StatCard } from "@/components/StatCard";
import { investmentTrades, dailyPrices, stockInfos } from "@/data/mockData";
import { TrendingUp, TrendingDown, BarChart3, Wallet, Calendar } from "lucide-react";
import { cn } from "@/lib/utils";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

function formatKRW(value: number) {
  return `₩${value.toLocaleString()}`;
}

function formatDate(d: string) {
  return d.replace(/-/g, ".");
}

/** 거래 기록에서 종목별 보유 현황 계산 */
function computeHoldings() {
  const map = new Map<string, { shares: number; totalCost: number; name: string; type: "stock" | "etf" }>();

  for (const t of investmentTrades) {
    const cur = map.get(t.ticker) || { shares: 0, totalCost: 0, name: t.name, type: t.type };
    if (t.action === "buy") {
      cur.totalCost += t.price * t.shares + (t.fee || 0);
      cur.shares += t.shares;
    } else {
      cur.shares -= t.shares;
      // 매도 시 비례 원가 차감
      const avgCost = cur.totalCost / (cur.shares + t.shares);
      cur.totalCost -= avgCost * t.shares;
    }
    map.set(t.ticker, cur);
  }

  return Array.from(map.entries())
    .filter(([, v]) => v.shares > 0)
    .map(([ticker, v]) => {
      const latestPrice = getLatestPrice(ticker);
      const avgPrice = Math.round(v.totalCost / v.shares);
      const currentValue = latestPrice * v.shares;
      const returnRate = ((currentValue - v.totalCost) / v.totalCost) * 100;
      return { ticker, name: v.name, type: v.type, shares: v.shares, avgPrice, currentPrice: latestPrice, totalCost: v.totalCost, currentValue, returnRate };
    });
}

function getLatestPrice(ticker: string) {
  const prices = dailyPrices.filter((p) => p.ticker === ticker);
  return prices.length > 0 ? prices[prices.length - 1].close : 0;
}

export default function Investments() {
  const [tab, setTab] = useState("portfolio");

  const holdings = useMemo(() => computeHoldings(), []);
  const totalValue = holdings.reduce((s, h) => s + h.currentValue, 0);
  const totalCost = holdings.reduce((s, h) => s + h.totalCost, 0);
  const totalReturn = totalValue - totalCost;
  const returnRate = totalCost > 0 ? ((totalReturn / totalCost) * 100).toFixed(2) : "0";

  // 일별 포트폴리오 가치 추적
  const dailyPortfolio = useMemo(() => {
    const dateSet = new Set(dailyPrices.map((p) => p.date));
    const dates = Array.from(dateSet).sort();

    return dates.map((date) => {
      let value = 0;
      for (const h of holdings) {
        const pricesUpToDate = dailyPrices.filter((p) => p.ticker === h.ticker && p.date <= date);
        const price = pricesUpToDate.length > 0 ? pricesUpToDate[pricesUpToDate.length - 1].close : h.avgPrice;
        value += price * h.shares;
      }
      return { date: date.slice(5), value, cost: totalCost };
    });
  }, [holdings, totalCost]);

  return (
    <AppLayout title="투자 관리">
      <div className="space-y-6 max-w-5xl">
        {/* 요약 */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard label="투자 평가액" value={formatKRW(totalValue)} icon={Wallet} iconClassName="bg-accent" />
          <StatCard
            label="총 수익"
            value={formatKRW(totalReturn)}
            change={`${Number(returnRate) > 0 ? "+" : ""}${returnRate}%`}
            changeType={totalReturn >= 0 ? "positive" : "negative"}
            icon={totalReturn >= 0 ? TrendingUp : TrendingDown}
            iconClassName={totalReturn >= 0 ? "bg-accent" : "bg-destructive/10"}
          />
          <StatCard label="총 투자원금" value={formatKRW(totalCost)} icon={BarChart3} iconClassName="bg-secondary" />
        </div>

        {/* 일별 추적 차트 */}
        <Card className="glass-card p-5">
          <h3 className="text-sm font-semibold mb-4">포트폴리오 일별 추이 (최근 30일)</h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dailyPortfolio}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
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
                  formatter={(value: number) => [formatKRW(value)]}
                />
                <Line type="monotone" dataKey="value" name="평가액" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="cost" name="원금" stroke="hsl(var(--muted-foreground))" strokeWidth={1} strokeDasharray="5 5" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* 탭: 포트폴리오 / 매매 내역 */}
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="portfolio">보유 종목</TabsTrigger>
            <TabsTrigger value="trades">매매 내역</TabsTrigger>
          </TabsList>

          <TabsContent value="portfolio">
            <Card className="glass-card">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-muted-foreground">
                      <th className="text-left px-5 py-2.5 font-medium">종목명</th>
                      <th className="text-right px-5 py-2.5 font-medium">수량</th>
                      <th className="text-right px-5 py-2.5 font-medium">평균단가</th>
                      <th className="text-right px-5 py-2.5 font-medium">현재가</th>
                      <th className="text-right px-5 py-2.5 font-medium">평가액</th>
                      <th className="text-right px-5 py-2.5 font-medium">수익률</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {holdings.map((h) => {
                      const positive = h.returnRate >= 0;
                      return (
                        <tr key={h.ticker} className="hover:bg-muted/30 transition-colors">
                          <td className="px-5 py-3">
                            <p className="font-medium">{h.name}</p>
                            <p className="text-xs text-muted-foreground">{h.ticker} · {h.type.toUpperCase()}</p>
                          </td>
                          <td className="px-5 py-3 text-right font-mono">{h.shares}</td>
                          <td className="px-5 py-3 text-right font-mono">{formatKRW(h.avgPrice)}</td>
                          <td className="px-5 py-3 text-right font-mono">{formatKRW(h.currentPrice)}</td>
                          <td className="px-5 py-3 text-right font-mono font-semibold">{formatKRW(h.currentValue)}</td>
                          <td className={cn("px-5 py-3 text-right font-mono font-semibold", positive ? "text-success" : "text-expense")}>
                            {positive ? "+" : ""}{h.returnRate.toFixed(2)}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="trades">
            <Card className="glass-card">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-muted-foreground">
                      <th className="text-left px-5 py-2.5 font-medium">일자</th>
                      <th className="text-left px-5 py-2.5 font-medium">종목명</th>
                      <th className="text-center px-5 py-2.5 font-medium">구분</th>
                      <th className="text-right px-5 py-2.5 font-medium">수량</th>
                      <th className="text-right px-5 py-2.5 font-medium">단가</th>
                      <th className="text-right px-5 py-2.5 font-medium">금액</th>
                      <th className="text-right px-5 py-2.5 font-medium">수수료</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {[...investmentTrades].sort((a, b) => b.date.localeCompare(a.date)).map((t) => (
                      <tr key={t.id} className="hover:bg-muted/30 transition-colors">
                        <td className="px-5 py-3 font-mono text-xs">{formatDate(t.date)}</td>
                        <td className="px-5 py-3">
                          <p className="font-medium">{t.name}</p>
                          <p className="text-xs text-muted-foreground">{t.ticker}</p>
                        </td>
                        <td className="px-5 py-3 text-center">
                          <span className={cn(
                            "text-xs font-semibold px-2 py-0.5 rounded-full",
                            t.action === "buy" ? "bg-accent text-accent-foreground" : "bg-destructive/10 text-expense"
                          )}>
                            {t.action === "buy" ? "매수" : "매도"}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-right font-mono">{t.shares}</td>
                        <td className="px-5 py-3 text-right font-mono">{formatKRW(t.price)}</td>
                        <td className="px-5 py-3 text-right font-mono font-semibold">{formatKRW(t.price * t.shares)}</td>
                        <td className="px-5 py-3 text-right font-mono text-muted-foreground">{formatKRW(t.fee || 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
}
