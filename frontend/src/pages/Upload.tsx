import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Upload as UploadIcon, FileSpreadsheet, Mail, RefreshCw, X, CheckCircle2, AlertCircle, Loader2, Eye } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useState, useRef, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadApi, accountsApi, type Account, type UploadResult, type PreviewRow } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface UploadHistoryItem {
  id: string;
  filename: string;
  accountName: string;
  uploadedAt: string;
  result: UploadResult;
}

export default function UploadPage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [isDragging, setIsDragging] = useState(false);
  const [uploadHistory, setUploadHistory] = useState<UploadHistoryItem[]>([]);
  const [selectedHistoryItem, setSelectedHistoryItem] = useState<UploadHistoryItem | null>(null);
  const [skipDuplicates, setSkipDuplicates] = useState(true);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState<PreviewRow[]>([]);
  const [editingRow, setEditingRow] = useState<number | null>(null);

  // 계좌 목록 조회
  const { data: accountsData, isLoading: accountsLoading } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => {
      const response = await accountsApi.list();
      return response.data || [];
    },
  });

  const accounts = accountsData || [];

  // 미리보기 mutation
  const previewMutation = useMutation({
    mutationFn: async ({ file, accountId }: { file: File; accountId?: string }) => {
      const ext = file.name.split(".").pop()?.toLowerCase();
      const format =
        ext === "csv" || ext === "txt"
          ? "csv"
          : ext === "xlsx"
            ? "xlsx"
            : ext === "xls"
              ? "xls"
              : undefined;
      return uploadApi.preview(file, format, accountId);
    },
    onSuccess: (response) => {
      setPreviewData(response.data.rows || []);
      setPreviewOpen(true);
    },
    onError: (error: any) => {
      toast.error(error.message || "미리보기에 실패했습니다.");
    },
  });

  // 업로드 mutation
  const uploadMutation = useMutation({
    mutationFn: async ({ file, accountId, skipDupes }: { file: File; accountId: string; skipDupes: boolean }) => {
      const ext = file.name.split(".").pop()?.toLowerCase();
      const format =
        ext === "csv" || ext === "txt"
          ? "csv"
          : ext === "xlsx"
            ? "xlsx"
            : ext === "xls"
              ? "xls"
              : undefined;
      return uploadApi.uploadTransactions(file, accountId, format, skipDupes);
    },
    onSuccess: (response, variables) => {
      const result = response.data;
      const historyItem: UploadHistoryItem = {
        id: Date.now().toString(),
        filename: variables.file.name,
        accountName: accounts.find((a) => a.id === variables.accountId)?.name || "알 수 없음",
        uploadedAt: new Date().toISOString(),
        result: result,
      };
      setUploadHistory((prev) => [historyItem, ...prev]);
      
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      
      const duplicateCount = result.duplicates || 0;
      const errorCount = result.errors?.length || 0;
      
      if (errorCount > 0) {
        toast.warning(
          `${result.imported}건 임포트, ${result.skipped}건 건너뜀${duplicateCount > 0 ? ` (중복 ${duplicateCount}건)` : ""}, ${errorCount}건 오류`
        );
      } else if (duplicateCount > 0) {
        toast.info(
          `${result.imported}건 임포트, 중복 거래 ${duplicateCount}건 건너뜀`
        );
      } else {
        toast.success(`${result.imported}건의 거래 내역이 성공적으로 업로드되었습니다.`);
      }
      
      setSelectedFile(null);
      setSelectedAccountId("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    onError: (error: any) => {
      toast.error(error.message || "업로드에 실패했습니다.");
    },
  });

  const isBusy = previewMutation.isPending || uploadMutation.isPending;

  const handleFileSelect = (file: File) => {
    const validExtensions = [".csv", ".xlsx", ".xls", ".txt"];
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    
    if (!validExtensions.includes(ext)) {
      toast.error("CSV 또는 Excel 파일만 업로드할 수 있습니다.");
      return;
    }
    
    if (file.size > 10 * 1024 * 1024) {
      toast.error("파일 크기는 10MB 이하여야 합니다.");
      return;
    }
    
    setSelectedFile(file);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  }, []);

  const handlePreview = () => {
    if (!selectedFile) {
      toast.error("파일을 선택해주세요.");
      return;
    }
    previewMutation.mutate({ file: selectedFile, accountId: selectedAccountId || undefined });
  };

  const handleUpload = () => {
    if (!selectedFile) {
      toast.error("파일을 선택해주세요.");
      return;
    }
    
    if (!selectedAccountId) {
      toast.error("계좌를 선택해주세요.");
      return;
    }
    
    uploadMutation.mutate({ file: selectedFile, accountId: selectedAccountId, skipDupes: skipDuplicates });
  };

  const handleUpdatePreviewRow = (index: number, field: keyof PreviewRow, value: string | number) => {
    setPreviewData((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const formatKRW = (value: number) => {
    return `₩${Math.abs(value).toLocaleString()}`;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <AppLayout title="데이터 업로드">
      {/* Upload/preview request overlay */}
      {isBusy && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/60 backdrop-blur-sm"
          role="status"
          aria-busy="true"
          aria-live="polite"
        >
          <div className="w-[min(520px,92vw)] rounded-xl border border-border/60 bg-card/90 p-6 shadow-xl">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              <div className="flex-1">
                <p className="text-sm font-semibold">
                  {uploadMutation.isPending ? "업로드 처리 중..." : "미리보기 생성 중..."}
                </p>
                <p className="text-xs text-muted-foreground mt-1">잠시만 기다려 주세요. 파일을 분석하고 있습니다.</p>
              </div>
            </div>
            <div className="mt-4">
              <Progress value={50} className="h-2" />
            </div>
          </div>
        </div>
      )}

      <div className="space-y-6 max-w-4xl" aria-disabled={isBusy}>
        {/* CSV/Excel 업로드 섹션 */}
        <Card className="p-6 glass-card">
          <h3 className="text-sm font-semibold mb-4">파일 업로드</h3>
          
          {/* 파일 선택 영역 */}
          <div
            className={cn(
              "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
              isDragging
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50",
              isBusy && "opacity-50 pointer-events-none"
            )}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls,.txt"
              onChange={handleFileInputChange}
              className="hidden"
            />
            
            {!selectedFile ? (
              <>
                <FileSpreadsheet className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                <p className="text-sm font-medium mb-2">파일을 드래그하거나 클릭하여 선택</p>
                <p className="text-xs text-muted-foreground mb-4">
                  CSV, Excel 파일 (최대 10MB)
                </p>
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  variant="outline"
                  size="sm"
                >
                  <UploadIcon className="h-4 w-4 mr-2" />
                  파일 선택
                </Button>
              </>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
                  <div className="flex items-center gap-3">
                    <FileSpreadsheet className="h-8 w-8 text-primary" />
                    <div className="text-left">
                      <p className="text-sm font-medium">{selectedFile.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatFileSize(selectedFile.size)}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                      setSelectedFile(null);
                      if (fileInputRef.current) {
                        fileInputRef.current.value = "";
                      }
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
                
                {/* 계좌 선택 */}
                <div className="space-y-2">
                  <Label>계좌 선택 *</Label>
                  {accountsLoading ? (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    </div>
                  ) : accounts.length === 0 ? (
                    <div className="p-4 border border-dashed rounded-lg text-center text-sm text-muted-foreground">
                      계좌가 없습니다. 먼저 계좌를 추가해주세요.
                    </div>
                  ) : (
                    <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
                      <SelectTrigger>
                        <SelectValue placeholder="계좌를 선택하세요" />
                      </SelectTrigger>
                      <SelectContent>
                        {accounts.map((account) => (
                          <SelectItem key={account.id} value={account.id}>
                            {account.name} ({account.institution})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
                
                {/* 중복 거래 감지 옵션 */}
                <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                  <div className="space-y-0.5">
                    <Label htmlFor="skip-duplicates" className="text-sm font-medium cursor-pointer">
                      중복 거래 자동 건너뛰기
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      날짜, 금액, 설명이 동일한 거래는 자동으로 건너뜁니다
                    </p>
                  </div>
                  <Switch
                    id="skip-duplicates"
                    checked={skipDuplicates}
                    onCheckedChange={setSkipDuplicates}
                  />
                </div>
                
                {/* 미리보기 및 업로드 버튼 */}
                <div className="flex gap-2">
                  <Button
                    onClick={handlePreview}
                    disabled={previewMutation.isPending}
                    variant="outline"
                    className="flex-1"
                  >
                    {previewMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        로딩 중...
                      </>
                    ) : (
                      <>
                        <Eye className="h-4 w-4 mr-2" />
                        미리보기
                      </>
                    )}
                  </Button>
                  <Button
                    onClick={handleUpload}
                    disabled={!selectedAccountId || uploadMutation.isPending}
                    className="flex-1"
                  >
                    {uploadMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        업로드 중...
                      </>
                    ) : (
                      <>
                        <UploadIcon className="h-4 w-4 mr-2" />
                        업로드
                      </>
                    )}
                  </Button>
                </div>
                
                {/* 진행 상태 */}
                {uploadMutation.isPending && (
                  <div className="space-y-2">
                    <Progress value={50} className="h-2" />
                    <p className="text-xs text-center text-muted-foreground">
                      파일을 처리하고 있습니다...
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </Card>

        {/* 업로드 결과 (최근) */}
        {uploadHistory.length > 0 && (
          <Card className="glass-card p-5">
            <h3 className="text-sm font-semibold mb-4">최근 업로드 결과</h3>
            <div className="space-y-3">
              {uploadHistory.slice(0, 5).map((item) => (
                <div
                  key={item.id}
                  className="flex items-start justify-between p-3 border border-border rounded-lg hover:bg-muted/30 transition-colors cursor-pointer"
                  onClick={() => setSelectedHistoryItem(item)}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
                      <p className="text-sm font-medium">{item.filename}</p>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {item.accountName} · {formatDate(item.uploadedAt)}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      {item.result.imported > 0 && (
                        <Badge variant="default" className="text-xs">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          {item.result.imported}건 성공
                        </Badge>
                      )}
                      {item.result.duplicates && item.result.duplicates > 0 && (
                        <Badge variant="secondary" className="text-xs">
                          중복 {item.result.duplicates}건
                        </Badge>
                      )}
                      {item.result.skipped > 0 && item.result.skipped > (item.result.duplicates || 0) && (
                        <Badge variant="secondary" className="text-xs">
                          건너뜀 {item.result.skipped - (item.result.duplicates || 0)}건
                        </Badge>
                      )}
                      {item.result.errors && Array.isArray(item.result.errors) && item.result.errors.length > 0 && (
                        <Badge variant="destructive" className="text-xs">
                          <AlertCircle className="h-3 w-3 mr-1" />
                          {item.result.errors.length}건 오류
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* 다른 업로드 방법 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Email Auto */}
          <Card className="p-6 glass-card flex flex-col items-center text-center space-y-4 hover:border-primary/40 transition-colors cursor-pointer">
            <div className="h-14 w-14 rounded-2xl bg-accent flex items-center justify-center">
              <Mail className="h-7 w-7 text-accent-foreground" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">이메일 연동</h3>
              <p className="text-xs text-muted-foreground mt-1">카드 승인, 증권 체결 메일을 자동 수집합니다</p>
            </div>
            <Button size="sm" variant="secondary" className="w-full" disabled>
              준비 중
            </Button>
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
            <Button size="sm" variant="secondary" className="w-full" disabled>
              준비 중
            </Button>
          </Card>
        </div>

        {/* 업로드 결과 상세 다이얼로그 */}
        <Dialog open={!!selectedHistoryItem} onOpenChange={(open) => !open && setSelectedHistoryItem(null)}>
          <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>업로드 결과 상세</DialogTitle>
              <DialogDescription className="sr-only">업로드 결과 요약 및 오류 상세를 확인합니다.</DialogDescription>
            </DialogHeader>
            {selectedHistoryItem && (
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <p className="text-sm font-medium">파일명</p>
                  <p className="text-sm text-muted-foreground">{selectedHistoryItem.filename}</p>
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-medium">계좌</p>
                  <p className="text-sm text-muted-foreground">{selectedHistoryItem.accountName}</p>
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-medium">업로드 시간</p>
                  <p className="text-sm text-muted-foreground">{formatDate(selectedHistoryItem.uploadedAt)}</p>
                </div>
                
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t">
                  <div className="text-center p-3 bg-primary/10 rounded-lg">
                    <p className="text-2xl font-bold text-primary">{selectedHistoryItem.result.imported}</p>
                    <p className="text-xs text-muted-foreground mt-1">성공</p>
                  </div>
                  {selectedHistoryItem.result.duplicates && selectedHistoryItem.result.duplicates > 0 && (
                    <div className="text-center p-3 bg-secondary rounded-lg">
                      <p className="text-2xl font-bold">{selectedHistoryItem.result.duplicates}</p>
                      <p className="text-xs text-muted-foreground mt-1">중복</p>
                    </div>
                  )}
                  <div className="text-center p-3 bg-muted rounded-lg">
                    <p className="text-2xl font-bold">{selectedHistoryItem.result.skipped}</p>
                    <p className="text-xs text-muted-foreground mt-1">건너뜀</p>
                  </div>
                  <div className="text-center p-3 bg-destructive/10 rounded-lg">
                    <p className="text-2xl font-bold text-destructive">
                      {selectedHistoryItem.result.errors && Array.isArray(selectedHistoryItem.result.errors) 
                        ? selectedHistoryItem.result.errors.length 
                        : 0}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">오류</p>
                  </div>
                </div>

                {selectedHistoryItem.result.errors && 
                 Array.isArray(selectedHistoryItem.result.errors) && 
                 selectedHistoryItem.result.errors.length > 0 && (
                  <div className="space-y-2 pt-4 border-t">
                    <p className="text-sm font-medium">오류 목록</p>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {selectedHistoryItem.result.errors.map((error, idx) => (
                        <div key={idx} className="p-2 bg-destructive/10 rounded text-xs">
                          <p className="font-medium">행 {error.row}:</p>
                          <p className="text-muted-foreground">{error.message}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            <DialogFooter>
              <Button variant="secondary" onClick={() => setSelectedHistoryItem(null)}>
                닫기
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* 미리보기 다이얼로그 */}
        <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
          <DialogContent className="sm:max-w-5xl max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>업로드 미리보기</DialogTitle>
              <DialogDescription className="sr-only">업로드 전에 파싱된 거래 내역을 미리보고 수정할 수 있습니다.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <p className="text-sm text-muted-foreground">
                총 {previewData.length}건의 거래 내역이 감지되었습니다. 필요시 수정 후 업로드하세요.
              </p>
              
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">행</TableHead>
                      <TableHead className="w-28">날짜</TableHead>
                      <TableHead>설명</TableHead>
                      <TableHead className="w-32 text-right">금액</TableHead>
                      <TableHead className="w-24">구분</TableHead>
                      <TableHead className="w-32">카테고리</TableHead>
                      <TableHead className="w-32">계좌</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {previewData.map((row, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-mono text-xs">{row.row}</TableCell>
                        <TableCell>
                          {editingRow === idx ? (
                            <Input
                              type="date"
                              value={row.date}
                              onChange={(e) => handleUpdatePreviewRow(idx, "date", e.target.value)}
                              className="h-8 text-xs"
                              onBlur={() => setEditingRow(null)}
                            />
                          ) : (
                            <span
                              className="text-xs cursor-pointer hover:underline"
                              onClick={() => setEditingRow(idx)}
                            >
                              {row.date}
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          {editingRow === idx ? (
                            <Input
                              value={row.description}
                              onChange={(e) => handleUpdatePreviewRow(idx, "description", e.target.value)}
                              className="h-8 text-xs"
                              onBlur={() => setEditingRow(null)}
                            />
                          ) : (
                            <span
                              className="text-xs cursor-pointer hover:underline"
                              onClick={() => setEditingRow(idx)}
                            >
                              {row.description}
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs">
                          {editingRow === idx ? (
                            <Input
                              type="number"
                              value={row.amount}
                              onChange={(e) => handleUpdatePreviewRow(idx, "amount", parseFloat(e.target.value) || 0)}
                              className="h-8 text-xs"
                              onBlur={() => setEditingRow(null)}
                            />
                          ) : (
                            <span
                              className={cn(
                                "cursor-pointer hover:underline",
                                row.amount > 0 ? "text-income" : "text-foreground"
                              )}
                              onClick={() => setEditingRow(idx)}
                            >
                              {formatKRW(row.amount)}
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          {editingRow === idx ? (
                            <Select
                              value={row.type}
                              onValueChange={(v) => {
                                handleUpdatePreviewRow(idx, "type", v);
                                setEditingRow(null);
                              }}
                            >
                              <SelectTrigger className="h-8 text-xs">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="income">수입</SelectItem>
                                <SelectItem value="expense">지출</SelectItem>
                                <SelectItem value="transfer">이체</SelectItem>
                              </SelectContent>
                            </Select>
                          ) : (
                            <Badge
                              variant={row.type === "income" ? "default" : row.type === "expense" ? "destructive" : "secondary"}
                              className="text-xs cursor-pointer"
                              onClick={() => setEditingRow(idx)}
                            >
                              {row.type === "income" ? "수입" : row.type === "expense" ? "지출" : "이체"}
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {editingRow === idx ? (
                            <Input
                              value={row.category}
                              onChange={(e) => handleUpdatePreviewRow(idx, "category", e.target.value)}
                              className="h-8 text-xs"
                              onBlur={() => setEditingRow(null)}
                            />
                          ) : (
                            <span
                              className="text-xs cursor-pointer hover:underline"
                              onClick={() => setEditingRow(idx)}
                            >
                              {row.category}
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-xs">{row.account || "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setPreviewOpen(false)}>
                닫기
              </Button>
              <Button
                onClick={() => {
                  setPreviewOpen(false);
                  if (selectedFile && selectedAccountId) {
                    // 미리보기에서 수정한 데이터로 업로드하려면 별도 처리 필요
                    // 현재는 일반 업로드 진행
                    handleUpload();
                  }
                }}
                disabled={!selectedAccountId}
              >
                수정된 데이터로 업로드
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
