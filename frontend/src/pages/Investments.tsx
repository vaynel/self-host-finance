import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { StatCard } from "@/components/StatCard";
import { TrendingUp, TrendingDown, BarChart3, Wallet, Bell, BellRing, ChevronDown, ChevronUp, Plus, Trash2, ShieldAlert, AlertTriangle, Loader2 } from "lucide-react";
import { investmentsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
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


function StockDailyChart({ ticker, name, avgPrice }: { ticker: string; name: string; avgPrice: number }) {
  const { data: priceData } = useQuery({
    queryKey: ["investments", "prices", ticker],
    queryFn: async () => {
      const response = await investmentsApi.getPrices(ticker, "30d");
      return response.data || [];
    },
    refetchInterval: 10 * 60 * 1000, // 10분 주기로 일별 시세(저장된 daily close) 갱신
  });

  const data = useMemo(() => {
    if (!priceData) return [];
    return priceData.map((p) => ({ date: p.date.slice(5), close: p.close }));
  }, [priceData]);

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
            <Line type="monotone" dataKey="close" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

const DEFAULT_GLOBAL_RULES: GlobalAlertRule[] = [
  { id: "g1", type: "cost_drop", percent: 10, active: true },
  { id: "g2", type: "peak_drop", percent: 15, active: true },
];

export default function Investments() {
  const [tab, setTab] = useState("portfolio");
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);
  const [globalRules, setGlobalRules] = useState<GlobalAlertRule[]>(DEFAULT_GLOBAL_RULES);

  // 새 룰 추가 폼
  const [newRuleType, setNewRuleType] = useState<GlobalAlertRule["type"]>("cost_drop");
  const [newRulePercent, setNewRulePercent] = useState("");

  // 보유 종목 조회
  const { data: holdingsData, isLoading: holdingsLoading } = useQuery({
    queryKey: ["investments", "holdings"],
    queryFn: async () => {
      const response = await investmentsApi.getHoldings();
      return response.data || [];
    },
    refetchInterval: 5 * 60 * 1000, // 5분 주기로 현재가/평가액 갱신
  });

  // 거래 내역 조회
  const { data: tradesData } = useQuery({
    queryKey: ["investments", "trades"],
    queryFn: async () => {
      const response = await investmentsApi.getTrades();
      return response.data || [];
    },
    refetchInterval: 5 * 60 * 1000,
  });

  const holdings = useMemo(() => {
    if (!holdingsData) return [];
    return holdingsData.map((h) => ({
      ticker: h.ticker,
      name: h.name,
      type: h.type,
      shares: h.shares,
      avgPrice: h.avgPrice,
      currentPrice: h.currentPrice,
      totalCost: h.avgPrice * h.shares,
      currentValue: h.totalValue,
      returnRate: h.profitLossRate,
    }));
  }, [holdingsData]);

  const totalValue = useMemo(() => holdings.reduce((s, h) => s + h.currentValue, 0), [holdings]);
  const totalCost = useMemo(() => holdings.reduce((s, h) => s + h.totalCost, 0), [holdings]);
  const totalReturn = totalValue - totalCost;
  const returnRate = totalCost > 0 ? ((totalReturn / totalCost) * 100).toFixed(2) : "0";

  const dailyPortfolio = useMemo(() => {
    // 간단한 추정: 실제로는 포트폴리오 가치 추적 API가 필요
    if (!holdingsData) return [];
    return [];
  }, [holdingsData, totalValue, totalCost]);

  // 종목별 고점 계산 (현재가를 고점으로 간주)
  const peakPrices = useMemo(() => {
    const map = new Map<string, number>();
    for (const h of holdings) {
      map.set(h.ticker, h.currentPrice);
    }
    return map;
  }, [holdings]);

  // 글로벌 룰 트리거 체크 - 어떤 종목이 어떤 룰에 걸리는지
  const triggeredItems = useMemo(() => {
    const results: { rule: GlobalAlertRule; ticker: string; name: string; currentPrice: number; threshold: number; actual: number }[] = [];
    for (const rule of globalRules) {
      if (!rule.active) continue;
      for (const h of holdings) {
        if (rule.type === "cost_drop") {
          const dropPercent = ((h.avgPrice - h.currentPrice) / h.avgPrice) * 100;
          if (dropPercent >= rule.percent) {
            results.push({ rule, ticker: h.ticker, name: h.name, currentPrice: h.currentPrice, threshold: rule.percent, actual: dropPercent });
          }
        } else if (rule.type === "peak_drop") {
          const peak = peakPrices.get(h.ticker) || h.currentPrice;
          const dropPercent = ((peak - h.currentPrice) / peak) * 100;
          if (dropPercent >= rule.percent) {
            results.push({ rule, ticker: h.ticker, name: h.name, currentPrice: h.currentPrice, threshold: rule.percent, actual: dropPercent });
          }
        }
      }
    }
    return results;
  }, [globalRules, holdings, peakPrices]);

  function handleToggleExpand(ticker: string) {
    setExpandedTicker((prev) => (prev === ticker ? null : ticker));
  }

  function handleAddRule() {
    if (!newRulePercent || Number(newRulePercent) <= 0) {
      toast.error("유효한 %값을 입력해주세요");
      return;
    }
    // 중복 체크
    const exists = globalRules.some((r) => r.type === newRuleType && r.percent === Number(newRulePercent));
    if (exists) {
      toast.error("동일한 조건의 룰이 이미 존재합니다");
      return;
    }
    const rule: GlobalAlertRule = {
      id: `g${Date.now()}`,
      type: newRuleType,
      percent: Number(newRulePercent),
      active: true,
    };
    setGlobalRules((prev) => [...prev, rule]);
    setNewRulePercent("");
    toast.success("알림 룰이 추가되었습니다");
  }

  function handleDeleteRule(id: string) {
    setGlobalRules((prev) => prev.filter((r) => r.id !== id));
  }

  function handleToggleRule(id: string) {
    setGlobalRules((prev) => prev.map((r) => (r.id === id ? { ...r, active: !r.active } : r)));
  }

  if (holdingsLoading) {
    return (
      <AppLayout title="투자 관리">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="투자 관리">
      <div className="space-y-6 max-w-5xl">
        {/* 트리거된 알림 배너 */}
        {triggeredItems.length > 0 && (
          <Card className="border-destructive/50 bg-destructive/5 p-4">
            <div className="flex items-center gap-2 mb-3">
              <BellRing className="h-4 w-4 text-destructive animate-pulse" />
              <span className="text-sm font-semibold text-destructive">매도 알림 트리거!</span>
              <Badge variant="destructive" className="text-[10px]">{triggeredItems.length}건</Badge>
            </div>
            <div className="space-y-2">
              {triggeredItems.map((item, i) => (
                <div key={i} className="flex items-center justify-between text-xs bg-background/50 rounded-lg px-3 py-2">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-3.5 w-3.5 text-destructive" />
                    <span className="font-medium">{item.name}</span>
                    <span className="text-muted-foreground">
                      {GLOBAL_RULE_INFO[item.rule.type].label} {item.rule.percent}% 룰
                    </span>
                  </div>
                  <div className="font-mono text-expense font-semibold">
                    -{item.actual.toFixed(1)}% ({formatKRW(item.currentPrice)})
                  </div>
                </div>
              ))}
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
                <Line type="monotone" dataKey="value" name="평가액" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="cost" name="원금" stroke="hsl(var(--muted-foreground))" strokeWidth={1} strokeDasharray="5 5" dot={false} isAnimationActive={false} />
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
              {triggeredItems.length > 0 && (
                <Badge variant="destructive" className="h-4 min-w-4 px-1 text-[10px] leading-none">
                  {triggeredItems.length}
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
                    {(tradesData || []).sort((a, b) => b.date.localeCompare(a.date)).map((t) => (
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

          {/* 알림 설정 - 글로벌 룰 */}
          <TabsContent value="alerts">
            <div className="space-y-4">
              {/* 설명 */}
              <Card className="glass-card p-5">
                <div className="flex items-start gap-3 mb-5">
                  <div className="h-9 w-9 rounded-lg bg-accent flex items-center justify-center flex-shrink-0">
                    <ShieldAlert className="h-4.5 w-4.5 text-accent-foreground" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">글로벌 매도 알림 룰</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      설정한 룰은 <span className="font-medium text-foreground">모든 보유 종목</span>에 일괄 적용됩니다. 조건이 충족되면 해당 종목에 알림이 표시됩니다.
                    </p>
                  </div>
                </div>

                {/* 룰 추가 폼 */}
                <div className="flex flex-wrap gap-3 items-end border-t border-border pt-4">
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground">조건 유형</label>
                    <Select value={newRuleType} onValueChange={(v) => setNewRuleType(v as GlobalAlertRule["type"])}>
                      <SelectTrigger className="w-48">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="cost_drop">투자원금 대비 하락</SelectItem>
                        <SelectItem value="peak_drop">고점 대비 하락</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground">하락 기준 (%)</label>
                    <Input
                      type="number"
                      className="w-28"
                      placeholder="10"
                      value={newRulePercent}
                      onChange={(e) => setNewRulePercent(e.target.value)}
                    />
                  </div>
                  <Button onClick={handleAddRule} size="sm">
                    <Plus className="h-3.5 w-3.5 mr-1" /> 룰 추가
                  </Button>
                </div>
              </Card>

              {/* 등록된 룰 목록 */}
              <Card className="glass-card">
                <div className="p-5 pb-3">
                  <h3 className="text-sm font-semibold">등록된 룰</h3>
                </div>
                {globalRules.length === 0 ? (
                  <div className="px-5 pb-5 text-sm text-muted-foreground">등록된 룰이 없습니다.</div>
                ) : (
                  <div className="divide-y divide-border">
                    {globalRules.map((rule) => {
                      const info = GLOBAL_RULE_INFO[rule.type];
                      const Icon = info.icon;
                      const matchCount = triggeredItems.filter((t) => t.rule.id === rule.id).length;
                      return (
                        <div key={rule.id} className={cn("px-5 py-4 flex items-center justify-between", matchCount > 0 && "bg-destructive/5")}>
                          <div className="flex items-center gap-3">
                            <div className={cn(
                              "h-9 w-9 rounded-lg flex items-center justify-center",
                              matchCount > 0 ? "bg-destructive/10" : "bg-muted"
                            )}>
                              <Icon className={cn("h-4 w-4", matchCount > 0 ? "text-destructive" : "text-muted-foreground")} />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <p className="text-sm font-medium">{info.label}</p>
                                <Badge variant="secondary" className="text-[10px] h-5 px-1.5 font-mono">
                                  -{rule.percent}%
                                </Badge>
                                {matchCount > 0 && (
                                  <Badge variant="destructive" className="text-[10px] h-5 px-1.5">
                                    {matchCount}종목 트리거
                                  </Badge>
                                )}
                              </div>
                              <p className="text-xs text-muted-foreground mt-0.5">{info.description}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={rule.active}
                              onCheckedChange={() => handleToggleRule(rule.id)}
                            />
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-muted-foreground hover:text-destructive"
                              onClick={() => handleDeleteRule(rule.id)}
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
