import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Landmark, TrendingUp, Plus, Trash2, ArrowLeftRight, ChevronDown, ChevronUp, ArrowUpRight, ArrowDownRight, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { getInstitutionIcon, getCategoryIcon } from "@/data/categoryIcons";
import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CurrencyInput } from "@/components/ui/currency-input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogClose,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { accountsApi, transactionsApi, type Account } from "@/lib/api";

const typeConfig = {
  bank: { label: "은행 계좌", icon: Landmark },
  investment: { label: "증권 계좌", icon: TrendingUp },
};

function formatKRW(value: number) {
  return `₩${Math.abs(value).toLocaleString()}`;
}

export default function Accounts() {
  const queryClient = useQueryClient();

  // 계좌 목록 조회
  const { data: accountList = [], isLoading: accountsLoading } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => {
      const response = await accountsApi.list();
      return response.data || [];
    },
  });

  // 계좌 추가 mutation
  const addAccountMutation = useMutation({
    mutationFn: async (data: { name: string; type: "bank" | "investment"; institution: string; balance: number }) => {
      return accountsApi.create(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      toast.success("계좌가 추가되었습니다");
    },
    onError: (error: any) => {
      toast.error(error.message || "계좌 추가 실패");
    },
  });

  // 계좌 삭제 mutation
  const deleteAccountMutation = useMutation({
    mutationFn: async (id: string) => {
      return accountsApi.delete(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      toast.success("계좌가 삭제되었습니다");
    },
    onError: (error: any) => {
      toast.error(error.message || "계좌 삭제 실패");
    },
  });

  // 계좌 이체 (거래 내역으로 생성)
  const transferMutation = useMutation({
    mutationFn: async (data: { fromId: string; toId: string; amount: number }) => {
      const fromAccount = accountList.find((a) => a.id === data.fromId);
      const toAccount = accountList.find((a) => a.id === data.toId);
      if (!fromAccount || !toAccount) throw new Error("계좌를 찾을 수 없습니다");

      // 출금 거래 생성
      await transactionsApi.create({
        date: new Date().toISOString().split("T")[0],
        description: `${toAccount.name}로 이체`,
        amount: -data.amount,
        type: "transfer",
        category: "이체",
        account: fromAccount.name,
      });

      // 입금 거래 생성
      await transactionsApi.create({
        date: new Date().toISOString().split("T")[0],
        description: `${fromAccount.name}에서 이체`,
        amount: data.amount,
        type: "transfer",
        category: "이체",
        account: toAccount.name,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      toast.success("이체가 완료되었습니다");
    },
    onError: (error: any) => {
      toast.error(error.message || "이체 실패");
    },
  });
  const [addOpen, setAddOpen] = useState(false);
  const [transferOpen, setTransferOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Account | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Add form state
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState<Account["type"]>("bank");
  const [newInstitution, setNewInstitution] = useState("");
  const [newAccountNumber, setNewAccountNumber] = useState("");
  const [newBalance, setNewBalance] = useState("");

  // Transfer form state
  const [fromId, setFromId] = useState("");
  const [toId, setToId] = useState("");
  const [transferAmount, setTransferAmount] = useState("");

  const grouped = {
    bank: accountList.filter((a) => a.type === "bank"),
    investment: accountList.filter((a) => a.type === "investment"),
  };

  // 계좌별 거래내역 조회 (expanded된 계좌만)
  const { data: accountTransactions } = useQuery({
    queryKey: ["transactions", { account: expandedId ? accountList.find((a) => a.id === expandedId)?.name : undefined }],
    queryFn: async () => {
      if (!expandedId) return [];
      const account = accountList.find((a) => a.id === expandedId);
      if (!account) return [];
      const response = await transactionsApi.list({ account: account.name, limit: 50 });
      return response.data || [];
    },
    enabled: !!expandedId,
  });

  const accountTxMap = useMemo(() => {
    if (!expandedId || !accountTransactions) return {};
    return { [expandedId]: accountTransactions };
  }, [expandedId, accountTransactions]);

  function handleAdd() {
    if (!newName.trim() || !newInstitution.trim()) {
      toast.error("계좌명과 금융기관을 입력해주세요");
      return;
    }
    addAccountMutation.mutate({
      name: newName.trim(),
      type: newType,
      institution: newInstitution.trim(),
      account_number: newAccountNumber.trim() || undefined,
      balance: Number(newBalance.replace(/,/g, "")) || 0,
    });
    setNewName("");
    setNewType("bank");
    setNewInstitution("");
    setNewAccountNumber("");
    setNewBalance("");
    setAddOpen(false);
  }

  function handleDelete() {
    if (!deleteTarget) return;
    deleteAccountMutation.mutate(deleteTarget.id);
    setDeleteTarget(null);
  }

  function handleTransfer() {
    const amount = Number(transferAmount.replace(/,/g, ""));
    if (!fromId || !toId || fromId === toId) {
      toast.error("출금 계좌와 입금 계좌를 다르게 선택해주세요");
      return;
    }
    if (!amount || amount <= 0) {
      toast.error("유효한 금액을 입력해주세요");
      return;
    }
    const fromAccount = accountList.find((a) => a.id === fromId);
    if (fromAccount && fromAccount.balance < amount) {
      toast.error("잔액이 부족합니다");
      return;
    }
    transferMutation.mutate({ fromId, toId, amount });
    setTransferAmount("");
    setFromId("");
    setToId("");
    setTransferOpen(false);
  }

  if (accountsLoading) {
    return (
      <AppLayout title="계좌 관리">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="계좌 관리">
      <div className="space-y-6 max-w-3xl">
        {/* Action Buttons */}
        <div className="flex gap-2">
          <Button size="sm" onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4 mr-1.5" />
            계좌 추가
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setTransferOpen(true)}>
            <ArrowLeftRight className="h-4 w-4 mr-1.5" />
            계좌 이체
          </Button>
        </div>

        {/* Account Groups */}
        {(Object.keys(grouped) as Array<keyof typeof grouped>).map((type) => {
          const config = typeConfig[type];
          const items = grouped[type];
          if (items.length === 0) return null;

          const total = items.reduce((s, a) => s + a.balance, 0);

          return (
            <div key={type} className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">{config.label}</h3>
                <span className="text-sm font-mono font-semibold text-foreground">
                  {formatKRW(total)}
                </span>
              </div>
              <div className="space-y-2">
                {items.map((account) => {
                  const instIcon = getInstitutionIcon(account.institution);
                  const Icon = instIcon.icon;
                  const isExpanded = expandedId === account.id;
                  const txList = accountTxMap[account.id] || [];

                  return (
                    <div key={account.id}>
                      <Card
                        className={cn(
                          "p-4 glass-card flex items-center justify-between hover:bg-muted/30 transition-colors group cursor-pointer",
                          isExpanded && "rounded-b-none border-b-0"
                        )}
                        onClick={() => setExpandedId(isExpanded ? null : account.id)}
                      >
                        <div className="flex items-center gap-3">
                          <div className={cn("h-10 w-10 rounded-xl flex items-center justify-center", instIcon.color)}>
                            <Icon className={cn("h-5 w-5", instIcon.iconColor)} />
                          </div>
                          <div>
                            <p className="text-sm font-medium">{account.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {account.institution}
                              {account.account_number && ` · ${account.account_number}`}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="text-right">
                            <p className="text-sm font-mono font-semibold text-foreground">
                              {formatKRW(account.balance)}
                            </p>
                            {account.lastSync && (
                              <p className="text-[10px] text-muted-foreground">동기화: {account.lastSync}</p>
                            )}
                          </div>
                          <div className="flex items-center gap-1">
                            {isExpanded ? (
                              <ChevronUp className="h-4 w-4 text-muted-foreground" />
                            ) : (
                              <ChevronDown className="h-4 w-4 text-muted-foreground" />
                            )}
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                              onClick={(e) => {
                                e.stopPropagation();
                                setDeleteTarget(account);
                              }}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </Card>

                      {/* Expanded: Balance Flow Chart + Transaction List */}
                      {isExpanded && (
                        <Card className="rounded-t-none border-t-0 glass-card overflow-hidden">
                          {txList && txList.length > 0 ? (
                            <div>
                              {/* Balance Flow Chart */}
                              <div className="px-5 pt-4 pb-2">
                                <p className="text-xs text-muted-foreground mb-2">잔액 흐름</p>
                                <div className="h-40">
                                  <ResponsiveContainer width="100%" height="100%">
                                    {(() => {
                                      const sorted = [...txList].sort((a, b) => a.date.localeCompare(b.date));
                                      let running = account.balance - sorted.reduce((s, tx) => s + tx.amount, 0);
                                      const chartData = sorted.map((tx) => {
                                        running += tx.amount;
                                        return { date: tx.date.slice(5), balance: running };
                                      });
                                      return (
                                        <LineChart data={chartData}>
                                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                                          <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
                                          <YAxis
                                            tick={{ fontSize: 10 }}
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
                                            formatter={(value: number) => [`₩${value.toLocaleString()}`, "잔액"]}
                                          />
                                          <Line
                                            type="monotone"
                                            dataKey="balance"
                                            stroke="hsl(var(--primary))"
                                            strokeWidth={2}
                                            dot={{ fill: "hsl(var(--primary))", r: 3 }}
                                            isAnimationActive={false}
                                          />
                                        </LineChart>
                                      );
                                    })()}
                                  </ResponsiveContainer>
                                </div>
                              </div>

                              {/* Transaction List */}
                              <div className="divide-y divide-border">
                                {txList.map((tx) => {
                                  const catIcon = getCategoryIcon(tx.category);
                                  const CatIcon = catIcon.icon;
                                  return (
                                    <div key={tx.id} className="px-5 py-3 flex items-center justify-between">
                                      <div className="flex items-center gap-3">
                                        <div className={cn("h-8 w-8 rounded-lg flex items-center justify-center", catIcon.color)}>
                                          <CatIcon className={cn("h-3.5 w-3.5", catIcon.iconColor)} />
                                        </div>
                                        <div>
                                          <p className="text-xs font-medium">{tx.description}</p>
                                          <p className="text-[10px] text-muted-foreground">{tx.date} · {tx.category}</p>
                                        </div>
                                      </div>
                                      <div className="flex items-center gap-1.5">
                                        {tx.amount > 0 ? (
                                          <ArrowUpRight className="h-3 w-3 text-income" />
                                        ) : (
                                          <ArrowDownRight className="h-3 w-3 text-expense" />
                                        )}
                                        <span className={cn(
                                          "text-xs font-mono font-semibold",
                                          tx.amount > 0 ? "text-income" : "text-foreground"
                                        )}>
                                          {tx.amount > 0 ? "+" : "-"}{formatKRW(tx.amount)}
                                        </span>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          ) : (
                            <div className="p-6 text-center text-xs text-muted-foreground">
                              거래 내역이 없습니다
                            </div>
                          )}
                        </Card>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}

        {accountList.length === 0 && (
          <div className="text-center py-16 text-muted-foreground text-sm">
            등록된 계좌가 없습니다. 계좌를 추가해주세요.
          </div>
        )}
      </div>

      {/* Add Account Dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>계좌 추가</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>계좌 유형</Label>
              <Select value={newType} onValueChange={(v) => setNewType(v as Account["type"])}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="bank">은행 계좌</SelectItem>
                  <SelectItem value="investment">증권 계좌</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>계좌명</Label>
              <Input placeholder="예: 국민은행 주거래" value={newName} onChange={(e) => setNewName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>금융기관</Label>
              <Input placeholder="예: KB국민은행" value={newInstitution} onChange={(e) => setNewInstitution(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>계좌번호 (선택)</Label>
              <Input placeholder="예: 123-456-789012" value={newAccountNumber} onChange={(e) => setNewAccountNumber(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>초기 잔액</Label>
              <CurrencyInput placeholder="0" value={newBalance} onChange={setNewBalance} />
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="secondary">취소</Button>
            </DialogClose>
            <Button onClick={handleAdd}>추가</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>계좌 삭제</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground py-2">
            <span className="font-medium text-foreground">{deleteTarget?.name}</span> 계좌를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.
          </p>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="secondary">취소</Button>
            </DialogClose>
            <Button variant="destructive" onClick={handleDelete}>삭제</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Transfer Dialog */}
      <Dialog open={transferOpen} onOpenChange={setTransferOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>계좌 이체</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>출금 계좌</Label>
              <Select value={fromId} onValueChange={setFromId}>
                <SelectTrigger><SelectValue placeholder="출금 계좌 선택" /></SelectTrigger>
                <SelectContent>
                  {accountList.map((a) => (
                    <SelectItem key={a.id} value={a.id}>
                      {a.name} ({formatKRW(a.balance)})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>입금 계좌</Label>
              <Select value={toId} onValueChange={setToId}>
                <SelectTrigger><SelectValue placeholder="입금 계좌 선택" /></SelectTrigger>
                <SelectContent>
                  {accountList.filter((a) => a.id !== fromId).map((a) => (
                    <SelectItem key={a.id} value={a.id}>
                      {a.name} ({formatKRW(a.balance)})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>이체 금액</Label>
              <CurrencyInput placeholder="0" value={transferAmount} onChange={setTransferAmount} />
              {fromId && (
                <p className="text-xs text-muted-foreground">
                  출금 가능: {formatKRW(accountList.find((a) => a.id === fromId)?.balance ?? 0)}
                </p>
              )}
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="secondary">취소</Button>
            </DialogClose>
            <Button onClick={handleTransfer}>이체</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
