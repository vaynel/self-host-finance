import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useState } from "react";
import { Plus, X, Pencil, Check, Webhook, Tag, Bell, Shield, Database, Trash2 } from "lucide-react";

interface Category {
  id: string;
  name: string;
  type: "income" | "expense" | "transfer";
  color: string;
}

interface WebhookConfig {
  id: string;
  name: string;
  url: string;
  events: string[];
  enabled: boolean;
}

const defaultCategories: Category[] = [
  { id: "1", name: "급여", type: "income", color: "hsl(172, 66%, 40%)" },
  { id: "2", name: "배당", type: "income", color: "hsl(152, 60%, 42%)" },
  { id: "3", name: "카페", type: "expense", color: "hsl(30, 60%, 50%)" },
  { id: "4", name: "쇼핑", type: "expense", color: "hsl(340, 60%, 55%)" },
  { id: "5", name: "구독", type: "expense", color: "hsl(280, 50%, 55%)" },
  { id: "6", name: "편의점", type: "expense", color: "hsl(100, 40%, 50%)" },
  { id: "7", name: "주거", type: "expense", color: "hsl(172, 66%, 40%)" },
  { id: "8", name: "배달", type: "expense", color: "hsl(20, 70%, 55%)" },
  { id: "9", name: "교통", type: "expense", color: "hsl(200, 60%, 50%)" },
  { id: "10", name: "식료품", type: "expense", color: "hsl(152, 60%, 42%)" },
  { id: "11", name: "운동", type: "expense", color: "hsl(262, 60%, 55%)" },
  { id: "12", name: "저축", type: "transfer", color: "hsl(38, 92%, 50%)" },
];

const eventOptions = [
  { label: "큰 지출 발생", value: "large_expense" },
  { label: "수입 입금", value: "income_received" },
  { label: "예산 초과", value: "budget_exceeded" },
  { label: "정기 리포트", value: "weekly_report" },
  { label: "이상 거래 감지", value: "anomaly_detected" },
];

export default function SettingsManagement() {
  // Category state
  const [categories, setCategories] = useState<Category[]>(defaultCategories);
  const [newCatName, setNewCatName] = useState("");
  const [newCatType, setNewCatType] = useState<"income" | "expense" | "transfer">("expense");
  const [editingCatId, setEditingCatId] = useState<string | null>(null);
  const [editCatName, setEditCatName] = useState("");

  // Webhook state
  const [webhooks, setWebhooks] = useState<WebhookConfig[]>([
    {
      id: "wh1",
      name: "Discord 알림",
      url: "",
      events: ["large_expense", "budget_exceeded"],
      enabled: true,
    },
  ]);
  const [showAddWebhook, setShowAddWebhook] = useState(false);
  const [newWhName, setNewWhName] = useState("");
  const [newWhUrl, setNewWhUrl] = useState("");
  const [newWhEvents, setNewWhEvents] = useState<string[]>([]);

  // Data settings
  const [retentionPeriod, setRetentionPeriod] = useState("12");
  const [currency, setCurrency] = useState("KRW");
  const [budgetAlert, setBudgetAlert] = useState(true);
  const [monthlyBudget, setMonthlyBudget] = useState("3000000");

  // Category CRUD
  const addCategory = () => {
    if (!newCatName.trim()) return;
    const id = Date.now().toString();
    setCategories([...categories, { id, name: newCatName.trim(), type: newCatType, color: "hsl(220, 15%, 50%)" }]);
    setNewCatName("");
  };

  const deleteCategory = (id: string) => {
    setCategories(categories.filter((c) => c.id !== id));
  };

  const startEditCategory = (cat: Category) => {
    setEditingCatId(cat.id);
    setEditCatName(cat.name);
  };

  const saveEditCategory = () => {
    if (!editCatName.trim() || !editingCatId) return;
    setCategories(categories.map((c) => (c.id === editingCatId ? { ...c, name: editCatName.trim() } : c)));
    setEditingCatId(null);
  };

  // Webhook CRUD
  const addWebhook = () => {
    if (!newWhName.trim() || !newWhUrl.trim()) return;
    setWebhooks([...webhooks, { id: Date.now().toString(), name: newWhName, url: newWhUrl, events: newWhEvents, enabled: true }]);
    setNewWhName("");
    setNewWhUrl("");
    setNewWhEvents([]);
    setShowAddWebhook(false);
  };

  const deleteWebhook = (id: string) => {
    setWebhooks(webhooks.filter((w) => w.id !== id));
  };

  const toggleWebhook = (id: string) => {
    setWebhooks(webhooks.map((w) => (w.id === id ? { ...w, enabled: !w.enabled } : w)));
  };

  const updateWebhookUrl = (id: string, url: string) => {
    setWebhooks(webhooks.map((w) => (w.id === id ? { ...w, url } : w)));
  };

  const toggleWebhookEvent = (whId: string, event: string) => {
    setWebhooks(webhooks.map((w) => {
      if (w.id !== whId) return w;
      const events = w.events.includes(event) ? w.events.filter((e) => e !== event) : [...w.events, event];
      return { ...w, events };
    }));
  };

  const typeLabel = (type: string) => {
    switch (type) {
      case "income": return "수입";
      case "expense": return "지출";
      case "transfer": return "이체";
      default: return type;
    }
  };

  const typeColor = (type: string) => {
    switch (type) {
      case "income": return "bg-primary/10 text-primary";
      case "expense": return "bg-destructive/10 text-destructive";
      case "transfer": return "bg-muted text-muted-foreground";
      default: return "bg-muted text-muted-foreground";
    }
  };

  return (
    <AppLayout title="설정 관리">
      <div className="space-y-6 max-w-3xl">

        {/* Category Management */}
        <Card className="glass-card p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Tag className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold">카테고리 관리</h3>
          </div>

          {/* Add Category */}
          <div className="flex gap-2">
            <Input
              placeholder="새 카테고리명"
              value={newCatName}
              onChange={(e) => setNewCatName(e.target.value)}
              className="flex-1 h-9 text-sm"
              onKeyDown={(e) => e.key === "Enter" && addCategory()}
            />
            <Select value={newCatType} onValueChange={(v) => setNewCatType(v as any)}>
              <SelectTrigger className="w-24 h-9 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="income" className="text-xs">수입</SelectItem>
                <SelectItem value="expense" className="text-xs">지출</SelectItem>
                <SelectItem value="transfer" className="text-xs">이체</SelectItem>
              </SelectContent>
            </Select>
            <Button size="sm" onClick={addCategory} className="h-9">
              <Plus className="h-3.5 w-3.5" />
            </Button>
          </div>

          {/* Category List - compact grid */}
          <div className="flex flex-wrap gap-1.5">
            {categories.map((cat) => (
              <div key={cat.id} className="group">
                {editingCatId === cat.id ? (
                  <div className="flex items-center gap-1 border border-primary rounded-md px-1.5 py-0.5">
                    <Input
                      value={editCatName}
                      onChange={(e) => setEditCatName(e.target.value)}
                      className="h-6 text-xs w-20 border-0 p-0 focus-visible:ring-0"
                      onKeyDown={(e) => e.key === "Enter" && saveEditCategory()}
                      autoFocus
                    />
                    <button onClick={saveEditCategory} className="text-primary hover:bg-primary/10 rounded p-0.5">
                      <Check className="h-3 w-3" />
                    </button>
                    <button onClick={() => setEditingCatId(null)} className="text-muted-foreground hover:bg-muted rounded p-0.5">
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ) : (
                  <Badge
                    variant="outline"
                    className={`text-xs gap-1.5 pr-1 cursor-default ${typeColor(cat.type)}`}
                  >
                    <span className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: cat.color }} />
                    {cat.name}
                    <button onClick={() => startEditCategory(cat)} className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-background/50 transition-opacity">
                      <Pencil className="h-2.5 w-2.5" />
                    </button>
                    <button onClick={() => deleteCategory(cat.id)} className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-destructive/20 text-destructive transition-opacity">
                      <X className="h-2.5 w-2.5" />
                    </button>
                  </Badge>
                )}
              </div>
          </div>
        </Card>

        {/* Discord Webhook */}
        <Card className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Webhook className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold">Discord Webhook 알림</h3>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowAddWebhook(!showAddWebhook)}
              className="text-xs h-8"
            >
              <Plus className="h-3.5 w-3.5 mr-1" /> 추가
            </Button>
          </div>

          {showAddWebhook && (
            <div className="border border-border rounded-lg p-4 space-y-3 bg-muted/30">
              <Input
                placeholder="Webhook 이름 (예: Discord 알림)"
                value={newWhName}
                onChange={(e) => setNewWhName(e.target.value)}
                className="h-9 text-sm"
              />
              <Input
                placeholder="https://discord.com/api/webhooks/..."
                value={newWhUrl}
                onChange={(e) => setNewWhUrl(e.target.value)}
                className="h-9 text-sm font-mono"
              />
              <div className="space-y-1.5">
                <label className="text-xs text-muted-foreground">알림 이벤트</label>
                <div className="flex flex-wrap gap-1.5">
                  {eventOptions.map((ev) => (
                    <Badge
                      key={ev.value}
                      variant={newWhEvents.includes(ev.value) ? "default" : "outline"}
                      className="cursor-pointer text-xs"
                      onClick={() =>
                        setNewWhEvents((prev) =>
                          prev.includes(ev.value) ? prev.filter((e) => e !== ev.value) : [...prev, ev.value]
                        )
                      }
                    >
                      {ev.label}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => setShowAddWebhook(false)}>취소</Button>
                <Button size="sm" onClick={addWebhook}>저장</Button>
              </div>
            </div>
          )}

          {webhooks.map((wh) => (
            <div key={wh.id} className="border border-border rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{wh.name}</span>
                  <Badge variant={wh.enabled ? "default" : "secondary"} className="text-[10px]">
                    {wh.enabled ? "활성" : "비활성"}
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
                  <Switch checked={wh.enabled} onCheckedChange={() => toggleWebhook(wh.id)} />
                  <button
                    onClick={() => deleteWebhook(wh.id)}
                    className="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
              <Input
                placeholder="https://discord.com/api/webhooks/..."
                value={wh.url}
                onChange={(e) => updateWebhookUrl(wh.id, e.target.value)}
                className="h-9 text-xs font-mono"
              />
              <div className="space-y-1.5">
                <label className="text-xs text-muted-foreground">알림 이벤트</label>
                <div className="flex flex-wrap gap-1.5">
                  {eventOptions.map((ev) => (
                    <Badge
                      key={ev.value}
                      variant={wh.events.includes(ev.value) ? "default" : "outline"}
                      className="cursor-pointer text-xs"
                      onClick={() => toggleWebhookEvent(wh.id, ev.value)}
                    >
                      {ev.label}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          ))}

          {webhooks.length === 0 && !showAddWebhook && (
            <p className="text-sm text-muted-foreground text-center py-4">
              등록된 Webhook이 없습니다
            </p>
          )}
        </Card>

        {/* Budget & Alerts */}
        <Card className="glass-card p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold">예산 및 알림</h3>
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="budget-alert" className="text-sm">월 예산 초과 알림</Label>
            <Switch id="budget-alert" checked={budgetAlert} onCheckedChange={setBudgetAlert} />
          </div>

          {budgetAlert && (
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">월 예산 한도</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">₩</span>
                <Input
                  type="number"
                  value={monthlyBudget}
                  onChange={(e) => setMonthlyBudget(e.target.value)}
                  className="pl-8 h-9 text-sm font-mono"
                />
              </div>
            </div>
          )}
        </Card>

        {/* Data & Security */}
        <Card className="glass-card p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold">데이터 및 보안</h3>
          </div>

          <div className="flex items-center justify-between">
            <Label className="text-sm">데이터 보관 기간</Label>
            <Select value={retentionPeriod} onValueChange={setRetentionPeriod}>
              <SelectTrigger className="w-32 h-9 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="6" className="text-xs">6개월</SelectItem>
                <SelectItem value="12" className="text-xs">12개월</SelectItem>
                <SelectItem value="24" className="text-xs">24개월</SelectItem>
                <SelectItem value="0" className="text-xs">무제한</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between">
            <Label className="text-sm">기본 통화</Label>
            <Select value={currency} onValueChange={setCurrency}>
              <SelectTrigger className="w-32 h-9 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="KRW" className="text-xs">₩ KRW</SelectItem>
                <SelectItem value="USD" className="text-xs">$ USD</SelectItem>
                <SelectItem value="JPY" className="text-xs">¥ JPY</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Separator />

          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold">보안</h3>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label htmlFor="two-factor" className="text-sm">2단계 인증</Label>
              <Switch id="two-factor" />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="login-alert" className="text-sm">로그인 알림</Label>
              <Switch id="login-alert" defaultChecked />
            </div>
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
