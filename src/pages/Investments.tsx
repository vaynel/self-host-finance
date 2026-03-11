import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { StatCard } from "@/components/StatCard";
import { investments } from "@/data/mockData";
import { TrendingUp, TrendingDown, BarChart3, Wallet } from "lucide-react";
import { cn } from "@/lib/utils";

function formatKRW(value: number) {
  return `₩${value.toLocaleString()}`;
}

export default function Investments() {
  const totalValue = investments.reduce((s, i) => s + i.currentPrice * i.shares, 0);
  const totalCost = investments.reduce((s, i) => s + i.avgPrice * i.shares, 0);
  const totalReturn = totalValue - totalCost;
  const returnRate = ((totalReturn / totalCost) * 100).toFixed(2);

  return (
    <AppLayout title="투자 관리">
      <div className="space-y-6 max-w-5xl">
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

        <Card className="glass-card">
          <div className="p-5 pb-3">
            <h3 className="text-sm font-semibold">보유 종목</h3>
          </div>
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
                {investments.map((inv) => {
                  const value = inv.currentPrice * inv.shares;
                  const cost = inv.avgPrice * inv.shares;
                  const ret = ((value - cost) / cost) * 100;
                  const positive = ret >= 0;

                  return (
                    <tr key={inv.id} className="hover:bg-muted/30 transition-colors">
                      <td className="px-5 py-3">
                        <div>
                          <p className="font-medium">{inv.name}</p>
                          <p className="text-xs text-muted-foreground">{inv.ticker} · {inv.type.toUpperCase()}</p>
                        </div>
                      </td>
                      <td className="px-5 py-3 text-right font-mono">{inv.shares}</td>
                      <td className="px-5 py-3 text-right font-mono">{formatKRW(inv.avgPrice)}</td>
                      <td className="px-5 py-3 text-right font-mono">{formatKRW(inv.currentPrice)}</td>
                      <td className="px-5 py-3 text-right font-mono font-semibold">{formatKRW(value)}</td>
                      <td className={cn(
                        "px-5 py-3 text-right font-mono font-semibold",
                        positive ? "text-success" : "text-expense"
                      )}>
                        {positive ? "+" : ""}{ret.toFixed(2)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
