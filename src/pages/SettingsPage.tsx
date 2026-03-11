import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

export default function SettingsPage() {
  return (
    <AppLayout title="설정">
      <div className="space-y-6 max-w-2xl">
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
      </div>
    </AppLayout>
  );
}
