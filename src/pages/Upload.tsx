import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload as UploadIcon, FileSpreadsheet, Mail, RefreshCw } from "lucide-react";

export default function UploadPage() {
  return (
    <AppLayout title="데이터 업로드">
      <div className="space-y-6 max-w-3xl">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* CSV Upload */}
          <Card className="p-6 glass-card flex flex-col items-center text-center space-y-4 hover:border-primary/40 transition-colors cursor-pointer">
            <div className="h-14 w-14 rounded-2xl bg-accent flex items-center justify-center">
              <FileSpreadsheet className="h-7 w-7 text-accent-foreground" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">CSV / Excel</h3>
              <p className="text-xs text-muted-foreground mt-1">은행, 카드, 증권 내역을 업로드합니다</p>
            </div>
            <Button size="sm" className="w-full">
              <UploadIcon className="h-3.5 w-3.5 mr-1.5" />
              파일 선택
            </Button>
          </Card>

          {/* Email Auto */}
          <Card className="p-6 glass-card flex flex-col items-center text-center space-y-4 hover:border-primary/40 transition-colors cursor-pointer">
            <div className="h-14 w-14 rounded-2xl bg-accent flex items-center justify-center">
              <Mail className="h-7 w-7 text-accent-foreground" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">이메일 연동</h3>
              <p className="text-xs text-muted-foreground mt-1">카드 승인, 증권 체결 메일을 자동 수집합니다</p>
            </div>
            <Button size="sm" variant="secondary" className="w-full">설정하기</Button>
          </Card>

          {/* Auto Sync */}
          <Card className="p-6 glass-card flex flex-col items-center text-center space-y-4 hover:border-primary/40 transition-colors cursor-pointer">
            <div className="h-14 w-14 rounded-2xl bg-accent flex items-center justify-center">
              <RefreshCw className="h-7 w-7 text-accent-foreground" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">자동 수집</h3>
              <p className="text-xs text-muted-foreground mt-1">주식 시세, 환율 데이터를 자동으로 수집합니다</p>
            </div>
            <Button size="sm" variant="secondary" className="w-full">설정하기</Button>
          </Card>
        </div>

        {/* Upload History */}
        <Card className="glass-card p-5">
          <h3 className="text-sm font-semibold mb-4">업로드 이력</h3>
          <div className="text-center py-8 text-muted-foreground text-sm">
            아직 업로드된 데이터가 없습니다
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
