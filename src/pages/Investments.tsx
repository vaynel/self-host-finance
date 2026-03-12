import { useState, useMemo } from "react";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { StatCard } from "@/components/StatCard";
import { investmentTrades, dailyPrices } from "@/data/mockData";
import { TrendingUp, TrendingDown, BarChart3, Wallet, Bell, BellRing, ChevronDown, ChevronUp, Plus, Trash2, ShieldAlert, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { toast } from "sonner";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";

function formatKRW(value: number) {
  return `₩${value.toLocaleString()}`;
}

function formatDate(d: string) {
  return d.replace(/-/g, ".");
}

/** 글로벌 알림 룰 - 모든 종목에 일괄 적용 */
interface GlobalAlertRule {
  id: string;
  type: "cost_drop" | "peak_drop";
  percent: number;
  active: boolean;
}

const GLOBAL_RULE_INFO: Record<GlobalAlertRule["type"], { label: string; description: string; icon: typeof ShieldAlert }> = {
  cost_drop: {
    label: "투자원금 대비 하락",
    description: "평균 매수가 대비 현재가가 설정한 % 이하로 하락 시 알림",
    icon: TrendingDown,
  },
  peak_drop: {
    label: "고점 대비 하락",
    description: "기간 내 최고가 대비 현재가가 설정한 % 이하로 하락 시 알림",
    icon: AlertTriangle,
  },
};

function computeHoldings() {
  const map = new Map<string, { shares: number; totalCost: number; name: string; type: "stock" | "etf" }>();

  for (const t of investmentTrades) {
    const cur = map.get(t.ticker) || { shares: 0, totalCost: 0, name: t.name, type: t.type };
    if (t.action === "buy") {
      cur.totalCost += t.price * t.shares + (t.fee || 0);
      cur.shares += t.shares;
    } else {
      cur.shares -= t.shares;
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

function StockDailyChart({ ticker, name, avgPrice }: { ticker: string; name: string; avgPrice: number }) {
  const data = useMemo(() => {
    return dailyPrices
      .filter((p) => p.ticker === ticker)
      .map((p) => ({ date: p.date.slice(5), close: p.close }));
  }, [ticker]);

  const min = Math.min(...data.map((d) => d.close));
  const max = Math.max(...data.map((d) => d.close));
  const padding = Math.round((max - min) * 0.15);

  return (
    <div className="px-5 pb-4 pt-2">
      <p className="text-xs text-muted-foreground mb-2">{name} 일별 시세 (최근 30일)</p>
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
            <YAxis
              domain={[min - padding, max + padding]}
              tick={{ fontSize: 10 }}
              stroke="hsl(var(--muted-foreground))"
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              formatter={(value: number) => [formatKRW(value), "종가"]}
            />
            <ReferenceLine
              y={avgPrice}
              stroke="hsl(var(--muted-foreground))"
              strokeDasharray="4 4"
              label={{ value: `평단 ${formatKRW(avgPrice)}`, position: "right", fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            />
            <Line type="monotone" dataKey="close" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// 기본 알림 룰 (데모)
const DEFAULT_ALERTS: AlertRule[] = [
  { id: "a1", ticker: "005930", name: "삼성전자", type: "price_above", value: 65000, active: true },
  { id: "a2", ticker: "035720", name: "카카오", type: "price_below", value: 45000, active: true },
  { id: "a3", ticker: "360750", name: "TIGER 미국S&P500", type: "return_above", value: 15, active: false },
];

export default function Investments() {
  const [tab, setTab] = useState("portfolio");
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<AlertRule[]>(DEFAULT_ALERTS);

  // 알림 추가 폼 상태
  const [newAlertTicker, setNewAlertTicker] = useState("");
  const [newAlertType, setNewAlertType] = useState<AlertRule["type"]>("price_above");
  const [newAlertValue, setNewAlertValue] = useState("");

  const holdings = useMemo(() => computeHoldings(), []);
  const totalValue = holdings.reduce((s, h) => s + h.currentValue, 0);
  const totalCost = holdings.reduce((s, h) => s + h.totalCost, 0);
  const totalReturn = totalValue - totalCost;
  const returnRate = totalCost > 0 ? ((totalReturn / totalCost) * 100).toFixed(2) : "0";

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

  // 알림 트리거 체크
  const triggeredAlerts = useMemo(() => {
    return alerts.filter((a) => {
      if (!a.active) return false;
      const h = holdings.find((h) => h.ticker === a.ticker);
      if (!h) return false;
      switch (a.type) {
        case "price_above": return h.currentPrice >= a.value;
        case "price_below": return h.currentPrice <= a.value;
        case "return_above": return h.returnRate >= a.value;
        case "return_below": return h.returnRate <= a.value;
      }
    });
  }, [alerts, holdings]);

  function handleToggleExpand(ticker: string) {
    setExpandedTicker((prev) => (prev === ticker ? null : ticker));
  }

  function handleAddAlert() {
    if (!newAlertTicker || !newAlertValue) {
      toast.error("종목과 값을 입력해주세요");
      return;
    }
    const h = holdings.find((h) => h.ticker === newAlertTicker);
    if (!h) return;
    const rule: AlertRule = {
      id: `a${Date.now()}`,
      ticker: newAlertTicker,
      name: h.name,
      type: newAlertType,
      value: Number(newAlertValue),
      active: true,
    };
    setAlerts((prev) => [...prev, rule]);
    setNewAlertTicker("");
    setNewAlertValue("");
    toast.success(`${h.name} 알림 룰이 추가되었습니다`);
  }

  function handleDeleteAlert(id: string) {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  }

  function handleToggleAlert(id: string) {
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, active: !a.active } : a)));
  }

  return (
    <AppLayout title="투자 관리">
      <div className="space-y-6 max-w-5xl">
        {/* 트리거된 알림 배너 */}
        {triggeredAlerts.length > 0 && (
          <Card className="border-primary/50 bg-primary/5 p-4">
            <div className="flex items-center gap-2 mb-2">
              <BellRing className="h-4 w-4 text-primary animate-pulse" />
              <span className="text-sm font-semibold text-primary">알림 트리거!</span>
            </div>
            <div className="space-y-1">
              {triggeredAlerts.map((a) => {
                const h = holdings.find((h) => h.ticker === a.ticker);
                return (
                  <p key={a.id} className="text-xs text-foreground">
                    <span className="font-medium">{a.name}</span>: {RULE_LABELS[a.type]} {a.value.toLocaleString()}{RULE_UNITS[a.type]}
                    {h && (
                      <span className="text-muted-foreground ml-1">
                        (현재: {a.type.includes("price") ? formatKRW(h.currentPrice) : `${h.returnRate.toFixed(2)}%`})
                      </span>
                    )}
                  </p>
                );
              })}
            </div>
          </Card>
        )}

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

        {/* 탭: 포트폴리오 / 매매 내역 / 알림 설정 */}
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="portfolio">보유 종목</TabsTrigger>
            <TabsTrigger value="trades">매매 내역</TabsTrigger>
            <TabsTrigger value="alerts" className="gap-1.5">
              <Bell className="h-3.5 w-3.5" />
              알림 설정
              {triggeredAlerts.length > 0 && (
                <Badge variant="destructive" className="h-4 min-w-4 px-1 text-[10px] leading-none">
                  {triggeredAlerts.length}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>

          {/* 보유 종목 + 클릭 시 일별 차트 */}
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
                      <th className="w-10"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {holdings.map((h) => {
                      const positive = h.returnRate >= 0;
                      const isExpanded = expandedTicker === h.ticker;
                      return (
                        <>
                          <tr
                            key={h.ticker}
                            className={cn(
                              "hover:bg-muted/30 transition-colors cursor-pointer border-b border-border",
                              isExpanded && "bg-muted/20"
                            )}
                            onClick={() => handleToggleExpand(h.ticker)}
                          >
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
                            <td className="px-2 py-3 text-muted-foreground">
                              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                            </td>
                          </tr>
                          {isExpanded && (
                            <tr key={`${h.ticker}-chart`}>
                              <td colSpan={7} className="bg-muted/10 border-b border-border">
                                <StockDailyChart ticker={h.ticker} name={h.name} avgPrice={h.avgPrice} />
                              </td>
                            </tr>
                          )}
                        </>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          </TabsContent>

          {/* 매매 내역 */}
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

          {/* 알림 설정 */}
          <TabsContent value="alerts">
            <div className="space-y-4">
              {/* 알림 추가 */}
              <Card className="glass-card p-5">
                <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
                  <Plus className="h-4 w-4" /> 새 알림 룰 추가
                </h3>
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground">종목</label>
                    <Select value={newAlertTicker} onValueChange={setNewAlertTicker}>
                      <SelectTrigger className="w-40">
                        <SelectValue placeholder="종목 선택" />
                      </SelectTrigger>
                      <SelectContent>
                        {holdings.map((h) => (
                          <SelectItem key={h.ticker} value={h.ticker}>{h.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground">조건</label>
                    <Select value={newAlertType} onValueChange={(v) => setNewAlertType(v as AlertRule["type"])}>
                      <SelectTrigger className="w-36">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="price_above">현재가 이상</SelectItem>
                        <SelectItem value="price_below">현재가 이하</SelectItem>
                        <SelectItem value="return_above">수익률 이상</SelectItem>
                        <SelectItem value="return_below">수익률 이하</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground">
                      값 ({newAlertType.includes("price") ? "원" : "%"})
                    </label>
                    <Input
                      type="number"
                      className="w-32"
                      placeholder={newAlertType.includes("price") ? "65000" : "15"}
                      value={newAlertValue}
                      onChange={(e) => setNewAlertValue(e.target.value)}
                    />
                  </div>
                  <Button onClick={handleAddAlert} size="sm">
                    추가
                  </Button>
                </div>
              </Card>

              {/* 알림 목록 */}
              <Card className="glass-card">
                <div className="p-5 pb-3">
                  <h3 className="text-sm font-semibold">등록된 알림 룰</h3>
                </div>
                {alerts.length === 0 ? (
                  <div className="px-5 pb-5 text-sm text-muted-foreground">등록된 알림이 없습니다.</div>
                ) : (
                  <div className="divide-y divide-border">
                    {alerts.map((a) => {
                      const h = holdings.find((h) => h.ticker === a.ticker);
                      const isTriggered = triggeredAlerts.some((t) => t.id === a.id);
                      return (
                        <div key={a.id} className={cn("px-5 py-3 flex items-center justify-between", isTriggered && "bg-primary/5")}>
                          <div className="flex items-center gap-3">
                            <div className={cn(
                              "h-8 w-8 rounded-lg flex items-center justify-center",
                              isTriggered ? "bg-primary/10" : "bg-muted"
                            )}>
                              {isTriggered ? (
                                <BellRing className="h-4 w-4 text-primary" />
                              ) : (
                                <Bell className="h-4 w-4 text-muted-foreground" />
                              )}
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <p className="text-sm font-medium">{a.name}</p>
                                {isTriggered && (
                                  <Badge variant="default" className="text-[10px] h-4 px-1.5">트리거됨</Badge>
                                )}
                                {!a.active && (
                                  <Badge variant="outline" className="text-[10px] h-4 px-1.5 text-muted-foreground">비활성</Badge>
                                )}
                              </div>
                              <p className="text-xs text-muted-foreground">
                                {RULE_LABELS[a.type]} {a.value.toLocaleString()}{RULE_UNITS[a.type]}
                                {h && (
                                  <span className="ml-1">
                                    (현재: {a.type.includes("price") ? formatKRW(h.currentPrice) : `${h.returnRate.toFixed(2)}%`})
                                  </span>
                                )}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 px-2 text-xs"
                              onClick={() => handleToggleAlert(a.id)}
                            >
                              {a.active ? "비활성" : "활성"}
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-muted-foreground hover:text-destructive"
                              onClick={() => handleDeleteAlert(a.id)}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
}
