import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { categoryKeywordsApi, settingsApi } from "@/lib/api";
import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

const CATEGORIES = [
  "식료품",
  "카페",
  "교통",
  "쇼핑",
  "구독",
  "주거",
  "의료",
  "교육",
  "운동",
  "배달",
  "편의점",
  "기타",
];

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [keywordDialogOpen, setKeywordDialogOpen] = useState(false);
  const [editingKeyword, setEditingKeyword] = useState<{ id: string; category: string; keyword: string; priority: string } | null>(null);
  const [newCategory, setNewCategory] = useState("");
  const [newKeyword, setNewKeyword] = useState("");
  const [newPriority, setNewPriority] = useState<"high" | "normal" | "low">("normal");
  const [discordWebhookInput, setDiscordWebhookInput] = useState("");

  const { data: settingsData } = useQuery({
    queryKey: ["user-settings"],
    queryFn: async () => {
      const res = await settingsApi.get();
      return res.data ?? null;
    },
  });

  const settingsMutation = useMutation({
    mutationFn: settingsApi.update,
    onSuccess: (res) => {
      queryClient.setQueryData(["user-settings"], res.data);
      queryClient.invalidateQueries({ queryKey: ["user-settings"] });
      setDiscordWebhookInput("");
      toast.success("알림 설정이 저장되었습니다.");
    },
    onError: (error: Error) => {
      toast.error(error.message || "저장에 실패했습니다.");
    },
  });

  const { data: keywordsData } = useQuery({
    queryKey: ["category-keywords"],
    queryFn: async () => {
      const response = await categoryKeywordsApi.list();
      return response.data || {};
    },
  });

  const createMutation = useMutation({
    mutationFn: categoryKeywordsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["category-keywords"] });
      toast.success("키워드가 추가되었습니다.");
      setKeywordDialogOpen(false);
      setNewCategory("");
      setNewKeyword("");
      setNewPriority("normal");
    },
    onError: (error: any) => {
      toast.error(error.message || "키워드 추가에 실패했습니다.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: categoryKeywordsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["category-keywords"] });
      toast.success("키워드가 삭제되었습니다.");
    },
    onError: () => {
      toast.error("키워드 삭제에 실패했습니다.");
    },
  });

  const handleCreateKeyword = () => {
    if (!newCategory || !newKeyword) {
      toast.error("카테고리와 키워드를 입력해주세요.");
      return;
    }
    createMutation.mutate({
      category: newCategory,
      keyword: newKeyword,
      priority: newPriority,
    });
  };

  const handleDeleteKeyword = (keywordId: string) => {
    if (confirm("이 키워드를 삭제하시겠습니까?")) {
      deleteMutation.mutate(keywordId);
    }
  };

  const keywords = keywordsData || {};

  return (
    <AppLayout title="설정">
      <div className="space-y-6 max-w-4xl">
        <Card className="p-5 glass-card space-y-5">
          <h3 className="text-sm font-semibold">Discord 알림 (자동매매 룰)</h3>
          <p className="text-xs text-muted-foreground">
            자동매매 룰이 실행되거나 알림 전용(alert_only)으로 트리거될 때 이 웹훅으로 메시지를 보냅니다. URL은 서버에 암호화되어 저장됩니다.
          </p>
          {settingsData?.discord_webhook_configured && settingsData.discord_webhook_masked && (
            <p className="text-xs text-muted-foreground font-mono break-all">
              현재: {settingsData.discord_webhook_masked}
            </p>
          )}
          <div className="space-y-2">
            <Label htmlFor="discord-webhook" className="text-sm">
              웹훅 URL
            </Label>
            <Input
              id="discord-webhook"
              type="password"
              autoComplete="off"
              placeholder="https://discord.com/api/webhooks/..."
              value={discordWebhookInput}
              onChange={(e) => setDiscordWebhookInput(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              disabled={settingsMutation.isPending || !discordWebhookInput.trim()}
              onClick={() =>
                settingsMutation.mutate({ discord_webhook_url: discordWebhookInput.trim() })
              }
            >
              저장
            </Button>
            <Button
              size="sm"
              variant="secondary"
              disabled={settingsMutation.isPending || !settingsData?.discord_webhook_configured}
              onClick={() => {
                if (!confirm("Discord 웹훅을 삭제할까요?")) return;
                settingsMutation.mutate({ discord_webhook_url: "" });
              }}
            >
              웹훅 삭제
            </Button>
          </div>
        </Card>

        <Card className="p-5 glass-card space-y-5">
          <h3 className="text-sm font-semibold">자동화 설정</h3>

          <div className="flex items-center justify-between">
            <Label htmlFor="auto-classify" className="text-sm">거래 자동 분류</Label>
            <Switch id="auto-classify" defaultChecked />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="duplicate" className="text-sm">중복 거래 자동 제거</Label>
            <Switch id="duplicate" defaultChecked />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="recurring" className="text-sm">반복 거래 자동 생성</Label>
            <Switch id="recurring" />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="email-sync" className="text-sm">이메일 자동 수집</Label>
            <Switch id="email-sync" />
          </div>
        </Card>

        <Card className="p-5 glass-card space-y-5">
          <h3 className="text-sm font-semibold">데이터 관리</h3>

          <div className="flex items-center justify-between">
            <Label htmlFor="auto-backup" className="text-sm">자동 백업</Label>
            <Switch id="auto-backup" defaultChecked />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="market-sync" className="text-sm">시세 자동 갱신</Label>
            <Switch id="market-sync" defaultChecked />
          </div>
        </Card>

        {/* 카테고리 키워드 관리 */}
        <Card className="p-5 glass-card space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">카테고리 자동 분류 키워드</h3>
            <Button size="sm" onClick={() => setKeywordDialogOpen(true)}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              키워드 추가
            </Button>
          </div>

          <p className="text-xs text-muted-foreground">
            거래 내역의 설명(description)에 포함된 키워드를 기반으로 자동으로 카테고리를 분류합니다.
          </p>

          <div className="space-y-4">
            {CATEGORIES.map((category) => {
              const categoryKeywords = keywords[category] || [];
              if (categoryKeywords.length === 0) return null;

              return (
                <div key={category} className="border border-border rounded-lg p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-medium">{category}</h4>
                    <Badge variant="secondary" className="text-xs">
                      {categoryKeywords.length}개
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {categoryKeywords.map((kw) => (
                      <div
                        key={kw.id}
                        className="flex items-center gap-1.5 px-2 py-1 bg-muted rounded-md text-xs"
                      >
                        <span>{kw.keyword}</span>
                        {kw.priority === "high" && (
                          <Badge variant="destructive" className="text-[10px] px-1">
                            높음
                          </Badge>
                        )}
                        <button
                          onClick={() => handleDeleteKeyword(kw.id)}
                          className="text-muted-foreground hover:text-destructive ml-1"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        {/* 키워드 추가 다이얼로그 */}
        <Dialog open={keywordDialogOpen} onOpenChange={setKeywordDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>키워드 추가</DialogTitle>
              <DialogDescription className="sr-only">카테고리 자동 분류에 사용할 키워드를 추가합니다.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>카테고리</Label>
                <Select value={newCategory} onValueChange={setNewCategory}>
                  <SelectTrigger>
                    <SelectValue placeholder="카테고리 선택" />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map((cat) => (
                      <SelectItem key={cat} value={cat}>
                        {cat}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>키워드</Label>
                <Input
                  placeholder="예: 스타벅스"
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>우선순위</Label>
                <Select value={newPriority} onValueChange={(v) => setNewPriority(v as "high" | "normal" | "low")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="high">높음 (우선 매칭)</SelectItem>
                    <SelectItem value="normal">보통</SelectItem>
                    <SelectItem value="low">낮음</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setKeywordDialogOpen(false)}>
                취소
              </Button>
              <Button onClick={handleCreateKeyword}>추가</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
