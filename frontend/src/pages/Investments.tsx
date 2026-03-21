import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { StatCard } from "@/components/StatCard";
import { TrendingUp, TrendingDown, BarChart3, Wallet, Bell, BellRing, ChevronDown, ChevronUp, Plus, Trash2, ShieldAlert, AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import { investmentsApi, accountsApi, type Account, type AutoTradeRule } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CurrencyInput } from "@/components/ui/currency-input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose,
} from "@/components/ui/dialog";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";

function formatKRW(value: number) {
  return `₩${value.toLocaleString()}`;
}

function formatDate(d: string) {
  return d.replace(/-/g, ".");
}

/** 글로벌 알림 룰 - 모든 종목에 일괄 적용 (서버 `auto_trade_global_rules`와 동기화) */
interface GlobalAlertRule {
  id: string;
  account_id: string;
  type: "cost_drop" | "peak_drop";
  percent: number;
  active: boolean;
  // 설정 모드: 알림만 / 자동매도 / 둘다
  mode: "alert_only" | "sell_only" | "alert_and_sell";
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

function modeLabelUi(m: GlobalAlertRule["mode"]) {
  return m === "alert_only" ? "알림만" : m === "sell_only" ? "매도까지" : "알림+매도";
}

function actionModeToApi(m: GlobalAlertRule["mode"]): AutoTradeRule["action_mode"] {
  return m === "alert_only" ? "alert_only" : m === "sell_only" ? "auto_sell" : "alert_and_sell";
}

function actionModeToUi(am: string): GlobalAlertRule["mode"] {
  return am === "alert_only" ? "alert_only" : am === "auto_sell" ? "sell_only" : "alert_and_sell";
}


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

export default function Investments() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState("portfolio");
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);

  // 새 룰 추가 폼
  const [newRuleType, setNewRuleType] = useState<GlobalAlertRule["type"]>("cost_drop");
  const [newRulePercent, setNewRulePercent] = useState("");
  const [newRuleMode, setNewRuleMode] = useState<GlobalAlertRule["mode"]>("alert_only");
  const [newRuleAccountId, setNewRuleAccountId] = useState<string>("");

  /** 포트폴리오에서 종목 펼침 시 — 해당 종목 전용 룰 추가 폼 */
  const [perStockRuleForm, setPerStockRuleForm] = useState<{
    trigger_kind: GlobalAlertRule["type"];
    percent: string;
    mode: GlobalAlertRule["mode"];
  }>({ trigger_kind: "cost_drop", percent: "", mode: "alert_only" });

  // peak_drop에서 사용하는 "구매 이후 고점(high-water mark)"을 유지합니다.
  const peakByTickerRef = useRef<Record<string, number>>({});
  const [peaksRevision, setPeaksRevision] = useState(0);

  // 거래 입력 다이얼로그
  const [tradeDialogOpen, setTradeDialogOpen] = useState(false);
  const [tradeForm, setTradeForm] = useState({
    ticker: "",
    name: "",
    action: "buy" as "buy" | "sell",
    date: new Date().toISOString().split("T")[0],
    shares: "",
    price: "",
    fee: "",
    accountId: "",
  });

  // KIS 연동 다이얼로그
  const [kisConnectDialogOpen, setKisConnectDialogOpen] = useState(false);
  const [kisConnectAccountId, setKisConnectAccountId] = useState<string>("");
  const [kisConnectForm, setKisConnectForm] = useState({
    broker_account_no: "",
    is_mock: false,
  });

  /** 보유 종목 탭: 동기화·KIS 연동 대상 투자 계좌 */
  const [portfolioAccountId, setPortfolioAccountId] = useState<string>("");

  // 계좌 목록 조회 (투자 계좌만)
  const { data: investmentAccounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => {
      const response = await accountsApi.list();
      return (response.data || []).filter((a: Account) => a.type === "investment");
    },
  });

  useEffect(() => {
    if (investmentAccounts.length === 0) {
      setPortfolioAccountId("");
      return;
    }
    setPortfolioAccountId((prev) => {
      const stillValid = investmentAccounts.some((a: Account) => a.id === prev);
      return stillValid ? prev : investmentAccounts[0].id;
    });
  }, [investmentAccounts]);

  const { data: globalRulesRaw = [], isLoading: globalRulesLoading } = useQuery({
    queryKey: ["investments", "rules", "global"],
    queryFn: async () => {
      const response = await investmentsApi.listGlobalRules();
      return response.data || [];
    },
  });

  const globalRules = useMemo((): GlobalAlertRule[] => {
    return globalRulesRaw.map((r) => {
      const am = r.action_mode;
      const mode: GlobalAlertRule["mode"] =
        am === "alert_only" ? "alert_only" : am === "auto_sell" ? "sell_only" : "alert_and_sell";
      return {
        id: r.id,
        account_id: r.account_id,
        type: r.trigger_kind,
        percent: r.trigger_percent,
        active: r.enabled,
        mode,
      };
    });
  }, [globalRulesRaw]);

  const { data: tickerRulesRaw = [], isLoading: tickerRulesLoading } = useQuery({
    queryKey: ["investments", "rules", "ticker"],
    queryFn: async () => {
      const response = await investmentsApi.listRules();
      return response.data || [];
    },
  });

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

  // 자동매매 실행 로그 조회
  const { data: ruleLogsData } = useQuery({
    queryKey: ["investments", "rules", "logs"],
    queryFn: async () => {
      const response = await investmentsApi.listRuleLogs(50);
      return response.data || [];
    },
    refetchInterval: 60 * 1000,
  });

  // 거래 생성 mutation
  const createTradeMutation = useMutation({
    mutationFn: async (data: typeof tradeForm) => {
      return investmentsApi.createTrade({
        ticker: data.ticker,
        action: data.action,
        date: data.date,
        shares: Number(data.shares),
        price: Number(data.price),
        fee: data.fee ? Number(data.fee) : undefined,
        accountId: data.accountId || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments", "holdings"] });
      queryClient.invalidateQueries({ queryKey: ["investments", "trades"] });
      toast.success("거래가 등록되었습니다");
      setTradeDialogOpen(false);
      setTradeForm({
        ticker: "",
        name: "",
        action: "buy",
        date: new Date().toISOString().split("T")[0],
        shares: "",
        price: "",
        fee: "",
        accountId: "",
      });
    },
    onError: (error: any) => {
      toast.error(error.message || "거래 등록 실패");
    },
  });

  // 계좌 동기화 mutation (백엔드 → 한국투자 OpenAPI 잔고/보유 조회)
  const syncAccountMutation = useMutation({
    mutationFn: async (accountId: string) => {
      return investmentsApi.syncAccount(accountId);
    },
    onMutate: () => {
      const id = toast.loading("한국투자 OpenAPI로 잔고·보유 동기화 중…");
      return { toastId: id };
    },
    onSuccess: (data, _accountId, ctx) => {
      if (ctx?.toastId) toast.dismiss(ctx.toastId);
      queryClient.invalidateQueries({ queryKey: ["investments", "holdings"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      toast.success(`동기화 완료: ${data.data?.holdingsCount || 0}개 종목, ${formatKRW(data.data?.cashBalance || 0)}`);
    },
    onError: (error: any, _accountId, ctx) => {
      if (ctx?.toastId) toast.dismiss(ctx.toastId);
      toast.error(error.message || "동기화 실패");
    },
  });

  const kisConnectMutation = useMutation({
    mutationFn: async (vars: {
      accountId: string;
      broker_account_no: string;
      is_mock: boolean;
    }) => {
      return investmentsApi.kisConnect(vars.accountId, {
        broker_account_no: vars.broker_account_no,
        is_mock: vars.is_mock,
      });
    },
    onSuccess: (res, vars) => {
      const d = res.data;
      const pc = d?.resolved_product_code;
      const auto = d?.product_code_auto;
      toast.success(
        auto && pc
          ? `KIS 연동 완료 · 상품코드 ${pc} 자동 설정`
          : pc
            ? `KIS 연동 완료 · 상품코드 ${pc}`
            : "KIS 연동 완료",
      );
      setKisConnectDialogOpen(false);
      syncAccountMutation.mutate(vars.accountId);
    },
    onError: (error: any) => {
      toast.error(error.message || "KIS 연동 실패");
    },
  });

  const addGlobalRuleMutation = useMutation({
    mutationFn: (payload: Parameters<typeof investmentsApi.createGlobalRule>[0]) =>
      investmentsApi.createGlobalRule(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments", "rules", "global"] });
      queryClient.invalidateQueries({ queryKey: ["investments", "rules", "triggers"] });
      toast.success("글로벌 룰이 저장되었습니다");
      setNewRulePercent("");
      setNewRuleMode("alert_only");
    },
    onError: (error: any) => {
      toast.error(error.message || "글로벌 룰 저장 실패");
    },
  });

  const updateGlobalRuleMutation = useMutation({
    mutationFn: ({ ruleId, enabled }: { ruleId: string; enabled: boolean }) =>
      investmentsApi.updateGlobalRule(ruleId, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments", "rules", "global"] });
      queryClient.invalidateQueries({ queryKey: ["investments", "rules", "triggers"] });
    },
    onError: (error: any) => {
      toast.error(error.message || "룰 상태 변경 실패");
    },
  });

  const deleteGlobalRuleMutation = useMutation({
    mutationFn: (ruleId: string) => investmentsApi.deleteGlobalRule(ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments", "rules", "global"] });
      queryClient.invalidateQueries({ queryKey: ["investments", "rules", "triggers"] });
      toast.success("룰이 삭제되었습니다");
    },
    onError: (error: any) => {
      toast.error(error.message || "룰 삭제 실패");
    },
  });

  const createTickerRuleMutation = useMutation({
    mutationFn: (payload: Parameters<typeof investmentsApi.createRule>[0]) => investmentsApi.createRule(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments", "rules", "ticker"] });
      queryClient.invalidateQueries({ queryKey: ["investments", "rules", "triggers"] });
      queryClient.invalidateQueries({ queryKey: ["investments", "rules", "logs"] });
      toast.success("종목 룰이 저장되었습니다");
      setPerStockRuleForm({ trigger_kind: "cost_drop", percent: "", mode: "alert_only" });
    },
    onError: (error: any) => {
      toast.error(error.message || "종목 룰 저장 실패");
    },
  });

  const updateTickerRuleMutation = useMutation({
    mutationFn: ({ ruleId, enabled }: { ruleId: string; enabled: boolean }) =>
      investmentsApi.updateRule(ruleId, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments", "rules", "ticker"] });
      queryClient.invalidateQueries({ queryKey: ["investments", "rules", "triggers"] });
    },
    onError: (error: any) => {
      toast.error(error.message || "종목 룰 상태 변경 실패");
    },
  });

  const deleteTickerRuleMutation = useMutation({
    mutationFn: (ruleId: string) => investmentsApi.deleteRule(ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investments", "rules", "ticker"] });
      queryClient.invalidateQueries({ queryKey: ["investments", "rules", "triggers"] });
      toast.success("종목 룰이 삭제되었습니다");
    },
    onError: (error: any) => {
      toast.error(error.message || "종목 룰 삭제 실패");
    },
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
      accountId: h.accountId,
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

  // holdings 갱신 시점마다 peak(high-water mark)를 갱신합니다.
  // - 초기 peak: avgPrice(=첫 구매가 기준을 최대한 반영)
  // - 이후: currentPrice가 더 높아지면 peak 갱신
  useEffect(() => {
    const tickers = new Set(holdings.map((h) => h.ticker));

    // 더 이상 보유하지 않는 종목 peak 제거
    for (const existingTicker of Object.keys(peakByTickerRef.current)) {
      if (!tickers.has(existingTicker)) {
        delete peakByTickerRef.current[existingTicker];
        setPeaksRevision((v) => v + 1);
      }
    }

    let changed = false;
    for (const h of holdings) {
      const prev = peakByTickerRef.current[h.ticker];
      const initPeak = h.avgPrice || h.currentPrice;
      if (prev === undefined) {
        peakByTickerRef.current[h.ticker] = initPeak;
        changed = true;
      } else if (h.currentPrice > prev) {
        peakByTickerRef.current[h.ticker] = h.currentPrice;
        changed = true;
      }
    }

    if (changed) setPeaksRevision((v) => v + 1);
  }, [holdings]);

  // 글로벌 룰 트리거 체크 - 어떤 종목이 어떤 룰에 걸리는지
  // 백엔드 트리거 상태 사용
  const { data: backendTriggered = [] } = useQuery({
    queryKey: ["investments", "rules", "triggers"],
    queryFn: async () => {
      const response = await investmentsApi.listRuleTriggers();
      return response.data || [];
    },
    refetchInterval: 60 * 1000,
  });
  const triggeredItems = useMemo(() => {
    return backendTriggered.map((t: any) => {
      const am: string = t.rule.action_mode;
      const mode =
        am === "alert_only" ? "alert_only" : am === "auto_sell" ? "sell_only" : "alert_and_sell";

      return {
        rule: {
          id: t.rule.id,
          account_id: t.rule.account_id ?? "",
          type: t.rule.trigger_kind as GlobalAlertRule["type"],
          percent: t.rule.trigger_percent,
          active: true,
          mode,
        } satisfies GlobalAlertRule,
        ticker: t.ticker,
        name: t.name,
        currentPrice: t.currentPrice,
        threshold: t.threshold,
        actual: t.actual,
        shares: t.shares,
        accountId: t.rule.account_id,
      };
    });
  }, [backendTriggered]);

  const alertTriggeredItems = useMemo(() => {
    return triggeredItems.filter((item) => item.rule.mode !== "sell_only");
  }, [triggeredItems]);

  function handleToggleExpand(ticker: string) {
    setExpandedTicker((prev) => (prev === ticker ? null : ticker));
  }

  function handleAddRule() {
    if (!newRulePercent || Number(newRulePercent) <= 0) {
      toast.error("유효한 %값을 입력해주세요");
      return;
    }
    const accountId = newRuleAccountId || (investmentAccounts[0]?.id || "");
    if (!accountId) {
      toast.error("적용할 투자 계좌를 선택해주세요");
      return;
    }
    const pct = Number(newRulePercent);
    const exists = globalRules.some(
      (r) => r.account_id === accountId && r.type === newRuleType && r.percent === pct,
    );
    if (exists) {
      toast.error("동일한 조건의 룰이 이미 존재합니다");
      return;
    }
    const action_mode =
      newRuleMode === "alert_only"
        ? "alert_only"
        : newRuleMode === "sell_only"
          ? "auto_sell"
          : "alert_and_sell";
    const payload: Parameters<typeof investmentsApi.createGlobalRule>[0] = {
      account_id: accountId,
      enabled: true,
      trigger_kind: newRuleType,
      trigger_percent: pct,
      action_mode,
      order_type: "market",
      sell_quantity_ratio: 1.0,
      cooldown_seconds: 300,
      limit_price: null,
    };
    addGlobalRuleMutation.mutate(payload);
  }

  function handleDeleteRule(id: string) {
    deleteGlobalRuleMutation.mutate(id);
  }

  function handleToggleRule(id: string) {
    const rule = globalRules.find((r) => r.id === id);
    if (!rule) return;
    updateGlobalRuleMutation.mutate({ ruleId: id, enabled: !rule.active });
  }

  function handleAddTickerRule(h: {
    ticker: string;
    accountId?: string;
    shares: number;
  }) {
    if (!perStockRuleForm.percent || Number(perStockRuleForm.percent) <= 0) {
      toast.error("유효한 %값을 입력해주세요");
      return;
    }
    const accountId = h.accountId || investmentAccounts[0]?.id;
    if (!accountId) {
      toast.error("계좌 정보가 없습니다. 동기화 후 다시 시도해주세요.");
      return;
    }
    const pct = Number(perStockRuleForm.percent);
    const dup = tickerRulesRaw.some(
      (r) =>
        r.ticker === h.ticker &&
        r.account_id === accountId &&
        r.trigger_kind === perStockRuleForm.trigger_kind &&
        r.trigger_percent === pct,
    );
    if (dup) {
      toast.error("동일한 조건의 종목 룰이 이미 있습니다");
      return;
    }
    const needsSell = perStockRuleForm.mode !== "alert_only";
    createTickerRuleMutation.mutate({
      account_id: accountId,
      ticker: h.ticker,
      side: "sell",
      enabled: true,
      order_type: needsSell ? "market" : "limit",
      quantity: h.shares,
      limit_price: null,
      cooldown_seconds: 300,
      trigger_kind: perStockRuleForm.trigger_kind,
      trigger_percent: pct,
      action_mode: actionModeToApi(perStockRuleForm.mode),
    });
  }

  function handleCreateTrade() {
    if (!tradeForm.ticker || !tradeForm.shares || !tradeForm.price) {
      toast.error("종목코드, 수량, 단가를 입력해주세요");
      return;
    }
    createTradeMutation.mutate(tradeForm);
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

          {/* 보유 종목 탭에 동기화 버튼 추가 */}
          <TabsContent value="portfolio">
            <div className="flex flex-col gap-2 mb-4">
              <p className="text-xs text-muted-foreground max-w-3xl">
                「동기화」는 <span className="text-foreground font-medium">한국투자증권 OpenAPI</span>로 연결된 계좌의 보유·예수금을 가져옵니다.
                「KIS 연동」에서는 <span className="text-foreground">계좌번호(연속계좌 앞 8자리, 또는 10자리 연속번호)</span>만 입력하면
                서버가 상품코드(ACNT_PRDT_CD)를 자동으로 맞춥니다.
              </p>
              <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:flex-wrap">
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">투자 계좌</Label>
                    {investmentAccounts.length === 0 ? (
                      <p className="text-xs text-muted-foreground">등록된 투자 계좌가 없습니다.</p>
                    ) : (
                      <Select value={portfolioAccountId} onValueChange={setPortfolioAccountId}>
                        <SelectTrigger className="w-[min(100%,280px)] sm:w-56">
                          <SelectValue placeholder="계좌 선택" />
                        </SelectTrigger>
                        <SelectContent>
                          {investmentAccounts.map((account: Account) => (
                            <SelectItem key={account.id} value={account.id}>
                              {account.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={
                        !portfolioAccountId ||
                        kisConnectMutation.isPending ||
                        syncAccountMutation.isPending
                      }
                      onClick={() => {
                        if (!portfolioAccountId) return;
                        setKisConnectAccountId(portfolioAccountId);
                        setKisConnectForm({ broker_account_no: "", is_mock: false });
                        setKisConnectDialogOpen(true);
                      }}
                    >
                      KIS 연동
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={!portfolioAccountId || syncAccountMutation.isPending}
                      onClick={() => portfolioAccountId && syncAccountMutation.mutate(portfolioAccountId)}
                    >
                      {syncAccountMutation.isPending ? (
                        <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                      )}
                      동기화
                    </Button>
                  </div>
                </div>
                <Button size="sm" onClick={() => setTradeDialogOpen(true)}>
                  <Plus className="h-3.5 w-3.5 mr-1.5" />
                  거래 입력
                </Button>
              </div>
            </div>

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
                      const resolvedAccountId = h.accountId ?? investmentAccounts[0]?.id;
                      const rulesForHolding = tickerRulesRaw.filter((r) => {
                        if (r.ticker !== h.ticker) return false;
                        if (!resolvedAccountId) return true;
                        return r.account_id === resolvedAccountId;
                      });
                      return (
                        <Fragment key={h.ticker}>
                          <tr
                            className={cn(
                              "hover:bg-muted/30 transition-colors cursor-pointer border-b border-border",
                              isExpanded && "bg-muted/20",
                            )}
                            onClick={() => handleToggleExpand(h.ticker)}
                          >
                            <td className="px-5 py-3">
                              <p className="font-medium">{h.name}</p>
                              <p className="text-xs text-muted-foreground">{h.ticker} · {h.type.toUpperCase()}</p>
                              {rulesForHolding.length > 0 && (
                                <p className="text-[10px] text-muted-foreground mt-0.5">
                                  종목 룰 {rulesForHolding.length}개
                                </p>
                              )}
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
                            <tr>
                              <td colSpan={7} className="bg-muted/10 border-b border-border">
                                <StockDailyChart ticker={h.ticker} name={h.name} avgPrice={h.avgPrice} />
                                <div
                                  className="border-t border-border px-5 py-4 space-y-4"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <div className="flex items-start gap-3">
                                    <div className="h-9 w-9 rounded-lg bg-secondary flex items-center justify-center flex-shrink-0">
                                      <Bell className="h-4 w-4 text-secondary-foreground" />
                                    </div>
                                    <div>
                                      <h4 className="text-sm font-semibold">이 종목 알림·매도 룰</h4>
                                      <p className="text-xs text-muted-foreground mt-0.5">
                                        이 종목에만 적용됩니다. 트리거 시 매도 수량은 현재 보유 수량({h.shares}) 기준입니다.
                                      </p>
                                    </div>
                                  </div>
                                  {rulesForHolding.length > 0 && (
                                    <div className="space-y-2">
                                      {rulesForHolding.map((r) => {
                                        const info = GLOBAL_RULE_INFO[r.trigger_kind];
                                        const Icon = info.icon;
                                        const m = actionModeToUi(r.action_mode);
                                        const matchN = triggeredItems.filter((t) => t.rule.id === r.id).length;
                                        return (
                                          <div
                                            key={r.id}
                                            className={cn(
                                              "flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border px-3 py-2 bg-background/80",
                                              matchN > 0 && "border-destructive/40 bg-destructive/5",
                                            )}
                                          >
                                            <div className="flex items-center gap-2 min-w-0">
                                              <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
                                              <span className="text-sm font-medium">{info.label}</span>
                                              <Badge variant="secondary" className="text-[10px] h-5 font-mono">
                                                -{r.trigger_percent}%
                                              </Badge>
                                              <Badge variant="outline" className="text-[10px] h-5">
                                                {modeLabelUi(m)}
                                              </Badge>
                                              {matchN > 0 && (
                                                <Badge variant="destructive" className="text-[10px] h-5">트리거</Badge>
                                              )}
                                            </div>
                                            <div className="flex items-center gap-2">
                                              <Switch
                                                checked={r.enabled}
                                                onCheckedChange={() =>
                                                  updateTickerRuleMutation.mutate({ ruleId: r.id, enabled: !r.enabled })
                                                }
                                                disabled={updateTickerRuleMutation.isPending}
                                              />
                                              <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8 text-muted-foreground hover:text-destructive"
                                                onClick={() => deleteTickerRuleMutation.mutate(r.id)}
                                                disabled={deleteTickerRuleMutation.isPending}
                                              >
                                                <Trash2 className="h-3.5 w-3.5" />
                                              </Button>
                                            </div>
                                          </div>
                                        );
                                      })}
                                    </div>
                                  )}
                                  <div className="flex flex-wrap gap-3 items-end pt-2 border-t border-dashed border-border">
                                    <div className="space-y-1.5">
                                      <label className="text-xs text-muted-foreground">조건</label>
                                      <Select
                                        value={perStockRuleForm.trigger_kind}
                                        onValueChange={(v) =>
                                          setPerStockRuleForm((f) => ({ ...f, trigger_kind: v as GlobalAlertRule["type"] }))
                                        }
                                      >
                                        <SelectTrigger className="w-44">
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
                                        className="w-24"
                                        placeholder="10"
                                        value={perStockRuleForm.percent}
                                        onChange={(e) =>
                                          setPerStockRuleForm((f) => ({ ...f, percent: e.target.value }))
                                        }
                                      />
                                    </div>
                                    <div className="space-y-1.5">
                                      <label className="text-xs text-muted-foreground">처리</label>
                                      <Select
                                        value={perStockRuleForm.mode}
                                        onValueChange={(v) =>
                                          setPerStockRuleForm((f) => ({ ...f, mode: v as GlobalAlertRule["mode"] }))
                                        }
                                      >
                                        <SelectTrigger className="w-36">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="alert_only">알림만</SelectItem>
                                          <SelectItem value="sell_only">매도까지</SelectItem>
                                          <SelectItem value="alert_and_sell">알림+매도</SelectItem>
                                        </SelectContent>
                                      </Select>
                                    </div>
                                    <Button
                                      size="sm"
                                      disabled={createTickerRuleMutation.isPending}
                                      onClick={() => handleAddTickerRule(h)}
                                    >
                                      <Plus className="h-3.5 w-3.5 mr-1" />
                                      룰 추가
                                    </Button>
                                  </div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </Fragment>
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
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground">처리 방식</label>
                    <Select value={newRuleMode} onValueChange={(v) => setNewRuleMode(v as GlobalAlertRule["mode"])}>
                      <SelectTrigger className="w-40">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="alert_only">알림만</SelectItem>
                        <SelectItem value="sell_only">매도까지</SelectItem>
                        <SelectItem value="alert_and_sell">알림 + 매도</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground">적용 계좌</label>
                    <Select value={newRuleAccountId} onValueChange={(v) => setNewRuleAccountId(v)}>
                      <SelectTrigger className="w-56">
                        <SelectValue placeholder="계좌 선택" />
                      </SelectTrigger>
                      <SelectContent>
                        {investmentAccounts.map((a: Account) => (
                          <SelectItem key={a.id} value={a.id}>
                            {a.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button onClick={handleAddRule} size="sm" disabled={addGlobalRuleMutation.isPending}>
                    <Plus className="h-3.5 w-3.5 mr-1" /> 룰 추가
                  </Button>
                </div>
              </Card>

              {/* 등록된 룰 목록 */}
              <Card className="glass-card">
                <div className="p-5 pb-3">
                  <h3 className="text-sm font-semibold">등록된 룰</h3>
                </div>
                {globalRulesLoading ? (
                  <div className="px-5 pb-5 flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" /> 룰 목록 불러오는 중…
                  </div>
                ) : globalRules.length === 0 ? (
                  <div className="px-5 pb-5 text-sm text-muted-foreground">등록된 룰이 없습니다. 위에서 추가하면 서버에 저장되며 새로고침 후에도 유지됩니다.</div>
                ) : (
                  <div className="divide-y divide-border">
                    {globalRules.map((rule) => {
                      const info = GLOBAL_RULE_INFO[rule.type];
                      const Icon = info.icon;
                      const matchCount = triggeredItems.filter((t) => t.rule.id === rule.id).length;
                      const accountLabel =
                        investmentAccounts.find((a: Account) => a.id === rule.account_id)?.name ?? rule.account_id;
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
                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 font-normal">
                                  {accountLabel}
                                </Badge>
                                <Badge variant="secondary" className="text-[10px] h-5 px-1.5 font-mono">
                                  -{rule.percent}%
                                </Badge>
                                <Badge
                                  variant={rule.mode === "alert_only" ? "secondary" : "destructive"}
                                  className="text-[10px] h-5 px-1.5 font-mono"
                                >
                                  {rule.mode === "alert_only" ? "알림만" : rule.mode === "sell_only" ? "매도까지" : "알림+매도"}
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
                              disabled={updateGlobalRuleMutation.isPending}
                            />
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-muted-foreground hover:text-destructive"
                              onClick={() => handleDeleteRule(rule.id)}
                              disabled={deleteGlobalRuleMutation.isPending}
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

              {/* 종목별 룰 요약 (서버 동기화) */}
              <Card className="glass-card">
                <div className="p-5 pb-3 space-y-1">
                  <h3 className="text-sm font-semibold">종목별 알림·매도 룰</h3>
                  <p className="text-xs text-muted-foreground">
                    특정 종목만 대상으로 합니다. 새 룰은 <span className="font-medium text-foreground">보유 종목</span> 탭에서 종목 행을 펼쳐 추가할 수 있습니다.
                  </p>
                </div>
                {tickerRulesLoading ? (
                  <div className="px-5 pb-5 flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" /> 불러오는 중…
                  </div>
                ) : tickerRulesRaw.length === 0 ? (
                  <div className="px-5 pb-5 text-sm text-muted-foreground">등록된 종목 룰이 없습니다.</div>
                ) : (
                  <div className="overflow-x-auto border-t border-border">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-muted-foreground text-xs">
                          <th className="text-left px-5 py-2.5 font-medium">종목</th>
                          <th className="text-left px-5 py-2.5 font-medium">계좌</th>
                          <th className="text-left px-5 py-2.5 font-medium">조건</th>
                          <th className="text-right px-5 py-2.5 font-medium">%</th>
                          <th className="text-left px-5 py-2.5 font-medium">처리</th>
                          <th className="text-center px-5 py-2.5 font-medium">활성</th>
                          <th className="w-24"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {tickerRulesRaw.map((r) => {
                          const info = GLOBAL_RULE_INFO[r.trigger_kind];
                          const accLabel =
                            investmentAccounts.find((a: Account) => a.id === r.account_id)?.name ?? r.account_id;
                          const holdingName =
                            holdings.find(
                              (x) => x.ticker === r.ticker && (x.accountId === r.accountId || !x.accountId),
                            )?.name ?? r.ticker;
                          const m = actionModeToUi(r.action_mode);
                          const matchN = triggeredItems.filter((t) => t.rule.id === r.id).length;
                          return (
                            <tr key={r.id} className={cn("hover:bg-muted/30", matchN > 0 && "bg-destructive/5")}>
                              <td className="px-5 py-2.5">
                                <p className="font-medium">{holdingName}</p>
                                <p className="text-[10px] text-muted-foreground font-mono">{r.ticker}</p>
                              </td>
                              <td className="px-5 py-2.5 text-xs text-muted-foreground">{accLabel}</td>
                              <td className="px-5 py-2.5 text-xs">{info.label}</td>
                              <td className="px-5 py-2.5 text-right font-mono text-xs">{r.trigger_percent}</td>
                              <td className="px-5 py-2.5">
                                <Badge variant="outline" className="text-[10px] h-5">
                                  {modeLabelUi(m)}
                                </Badge>
                                {matchN > 0 && (
                                  <Badge variant="destructive" className="text-[10px] h-5 ml-1">트리거</Badge>
                                )}
                              </td>
                              <td className="px-5 py-2.5 text-center">
                                <Switch
                                  checked={r.enabled}
                                  onCheckedChange={() =>
                                    updateTickerRuleMutation.mutate({ ruleId: r.id, enabled: !r.enabled })
                                  }
                                  disabled={updateTickerRuleMutation.isPending}
                                />
                              </td>
                              <td className="px-5 py-2.5">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 text-destructive hover:text-destructive"
                                  onClick={() => deleteTickerRuleMutation.mutate(r.id)}
                                  disabled={deleteTickerRuleMutation.isPending}
                                >
                                  삭제
                                </Button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>

              {/* 최근 실행 로그 */}
              <Card className="glass-card">
                <div className="p-5 pb-3">
                  <h3 className="text-sm font-semibold">최근 실행 로그</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b text-muted-foreground">
                        <th className="text-left px-5 py-2.5 font-medium">시간</th>
                        <th className="text-left px-5 py-2.5 font-medium">계좌</th>
                        <th className="text-left px-5 py-2.5 font-medium">종목</th>
                        <th className="text-left px-5 py-2.5 font-medium">상태</th>
                        <th className="text-left px-5 py-2.5 font-medium">사유</th>
                        <th className="text-left px-5 py-2.5 font-medium">주문ID</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {(ruleLogsData || []).map((r: any) => (
                        <tr key={r.id} className="hover:bg-muted/30">
                          <td className="px-5 py-2.5 font-mono">{r.created_at?.replace("T", " ").slice(0, 19)}</td>
                          <td className="px-5 py-2.5">{r.account_id}</td>
                          <td className="px-5 py-2.5">{r.ticker}</td>
                          <td className="px-5 py-2.5">
                            <span className={cn(
                              "px-2 py-0.5 rounded-full font-semibold",
                              r.status === "triggered" ? "bg-accent text-accent-foreground" :
                              r.status === "failed" ? "bg-destructive/10 text-expense" : "bg-muted text-muted-foreground"
                            )}>
                              {r.status}
                            </span>
                          </td>
                          <td className="px-5 py-2.5 text-muted-foreground">{r.reason || "-"}</td>
                          <td className="px-5 py-2.5 font-mono">{r.order_id || "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* KIS 연동 다이얼로그 */}
        <Dialog open={kisConnectDialogOpen} onOpenChange={setKisConnectDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>KIS 계좌 연동</DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                한국투자 앱에 보이는 연속계좌 앞 8자리를 입력하세요. 10자리(앞8+뒤2)를 붙여 넣어도 됩니다. 상품코드는 서버가 자동으로 찾습니다.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label>계좌번호 (연속계좌)</Label>
                <Input
                  placeholder="예: 12345678 또는 1234567801"
                  value={kisConnectForm.broker_account_no}
                  onChange={(e) => setKisConnectForm({ ...kisConnectForm, broker_account_no: e.target.value })}
                />
              </div>
              <div className="flex items-center justify-between gap-3">
                <Label className="text-sm">모의투자</Label>
                <Switch
                  checked={kisConnectForm.is_mock}
                  onCheckedChange={(v) => setKisConnectForm({ ...kisConnectForm, is_mock: v })}
                />
              </div>
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="secondary">취소</Button>
              </DialogClose>
              <Button
                onClick={() =>
                  kisConnectMutation.mutate({
                    accountId: kisConnectAccountId,
                    broker_account_no: kisConnectForm.broker_account_no,
                    is_mock: kisConnectForm.is_mock,
                  })
                }
                disabled={
                  kisConnectMutation.isPending ||
                  !kisConnectAccountId ||
                  !kisConnectForm.broker_account_no.trim()
                }
              >
                {kisConnectMutation.isPending ? "연동 중..." : "연동"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* 거래 입력 다이얼로그 */}
        <Dialog open={tradeDialogOpen} onOpenChange={setTradeDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>투자 거래 입력</DialogTitle>
              <DialogDescription className="sr-only">매수/매도 거래를 수동으로 입력합니다.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label>종목코드</Label>
                <Input
                  placeholder="예: 005930"
                  value={tradeForm.ticker}
                  onChange={(e) => setTradeForm({ ...tradeForm, ticker: e.target.value.toUpperCase() })}
                />
              </div>
              <div className="space-y-2">
                <Label>종목명 (선택)</Label>
                <Input
                  placeholder="예: 삼성전자"
                  value={tradeForm.name}
                  onChange={(e) => setTradeForm({ ...tradeForm, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>구분</Label>
                <Select value={tradeForm.action} onValueChange={(v) => setTradeForm({ ...tradeForm, action: v as "buy" | "sell" })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="buy">매수</SelectItem>
                    <SelectItem value="sell">매도</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>거래일</Label>
                <Input
                  type="date"
                  value={tradeForm.date}
                  onChange={(e) => setTradeForm({ ...tradeForm, date: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>수량</Label>
                <Input
                  type="number"
                  placeholder="0"
                  value={tradeForm.shares}
                  onChange={(e) => setTradeForm({ ...tradeForm, shares: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>단가</Label>
                <CurrencyInput
                  placeholder="0"
                  value={tradeForm.price}
                  onChange={(v) => setTradeForm({ ...tradeForm, price: v })}
                />
              </div>
              <div className="space-y-2">
                <Label>수수료 (선택)</Label>
                <CurrencyInput
                  placeholder="0"
                  value={tradeForm.fee}
                  onChange={(v) => setTradeForm({ ...tradeForm, fee: v })}
                />
              </div>
              {investmentAccounts.length > 0 && (
                <div className="space-y-2">
                  <Label>계좌 (선택)</Label>
                  <Select value={tradeForm.accountId} onValueChange={(v) => setTradeForm({ ...tradeForm, accountId: v })}>
                    <SelectTrigger><SelectValue placeholder="계좌 선택 (없으면 기본 계좌)" /></SelectTrigger>
                    <SelectContent>
                      {investmentAccounts.map((account: Account) => (
                        <SelectItem key={account.id} value={account.id}>
                          {account.name} ({formatKRW(account.balance)})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="secondary">취소</Button>
              </DialogClose>
              <Button onClick={handleCreateTrade} disabled={createTradeMutation.isPending}>
                {createTradeMutation.isPending ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                    등록 중...
                  </>
                ) : (
                  "등록"
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
