import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { transactions as initialTransactions } from "@/data/mockData";
import { Search, Filter, Calendar, X, Check, Pencil } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { getCategoryIcon } from "@/data/categoryIcons";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";

function formatKRWFull(value: number) {
  return `₩${Math.abs(value).toLocaleString()}`;
}

type FilterType = "all" | "income" | "expense" | "transfer";

const allCategories = [
  "급여", "카페", "쇼핑", "구독", "편의점", "주거", "배달", "교통", "배당", "저축", "식료품", "운동",
];

const allAccounts = ["국민은행", "신한카드", "삼성카드", "키움증권"];

export default function Transactions() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterType>("all");
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [txList, setTxList] = useState(initialTransactions);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editCategory, setEditCategory] = useState("");

  const activeFilterCount =
    selectedCategories.length + selectedAccounts.length + (dateFrom ? 1 : 0) + (dateTo ? 1 : 0);

  const filtered = txList.filter((tx) => {
    const matchSearch =
      tx.description.toLowerCase().includes(search.toLowerCase()) ||
      tx.category.toLowerCase().includes(search.toLowerCase());
    const matchFilter = filter === "all" || tx.type === filter;
    const matchCategory =
      selectedCategories.length === 0 || selectedCategories.includes(tx.category);
    const matchAccount =
      selectedAccounts.length === 0 || selectedAccounts.includes(tx.account);
    const matchDateFrom = !dateFrom || tx.date >= dateFrom;
    const matchDateTo = !dateTo || tx.date <= dateTo;
    return matchSearch && matchFilter && matchCategory && matchAccount && matchDateFrom && matchDateTo;
  });

  const filters: { label: string; value: FilterType }[] = [
    { label: "전체", value: "all" },
    { label: "수입", value: "income" },
    { label: "지출", value: "expense" },
    { label: "이체", value: "transfer" },
  ];

  const clearAllFilters = () => {
    setSelectedCategories([]);
    setSelectedAccounts([]);
    setDateFrom("");
    setDateTo("");
  };

  const toggleCategory = (cat: string) => {
    setSelectedCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  };

  const toggleAccount = (acc: string) => {
    setSelectedAccounts((prev) =>
      prev.includes(acc) ? prev.filter((a) => a !== acc) : [...prev, acc]
    );
  };

  const startEditCategory = (id: string, currentCategory: string) => {
    setEditingId(id);
    setEditCategory(currentCategory);
  };

  const saveCategory = (id: string) => {
    setTxList((prev) =>
      prev.map((tx) => (tx.id === id ? { ...tx, category: editCategory } : tx))
    );
    setEditingId(null);
  };

  return (
    <AppLayout title="거래 내역">
      <div className="space-y-4 max-w-4xl">
        {/* Search + Type Filter + Advanced Filter Toggle */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="거래명, 카테고리 검색..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="flex gap-1.5">
            {filters.map((f) => (
              <Button
                key={f.value}
                variant={filter === f.value ? "default" : "secondary"}
                size="sm"
                onClick={() => setFilter(f.value)}
                className="text-xs"
              >
                {f.label}
              </Button>
            ))}
            <Button
              variant={showFilters ? "default" : "outline"}
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className="text-xs relative"
            >
              <Filter className="h-3.5 w-3.5 mr-1" />
              필터
              {activeFilterCount > 0 && (
                <Badge variant="secondary" className="ml-1 h-4 w-4 p-0 flex items-center justify-center text-[10px] rounded-full bg-primary text-primary-foreground">
                  {activeFilterCount}
                </Badge>
              )}
            </Button>
          </div>
        </div>

        {/* Advanced Filters Panel */}
        {showFilters && (
          <Card className="glass-card p-4 space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold">상세 필터</h4>
              {activeFilterCount > 0 && (
                <Button variant="ghost" size="sm" onClick={clearAllFilters} className="text-xs h-7 text-muted-foreground">
                  <X className="h-3 w-3 mr-1" /> 초기화
                </Button>
              )}
            </div>

            {/* Date Range */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground">기간</label>
              <div className="flex gap-2 items-center">
                <div className="relative flex-1">
                  <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="pl-8 text-xs h-9"
                  />
                </div>
                <span className="text-xs text-muted-foreground">~</span>
                <div className="relative flex-1">
                  <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="pl-8 text-xs h-9"
                  />
                </div>
              </div>
            </div>

            {/* Category Filter */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground">카테고리</label>
              <div className="flex flex-wrap gap-1.5">
                {allCategories.map((cat) => (
                  <Badge
                    key={cat}
                    variant={selectedCategories.includes(cat) ? "default" : "outline"}
                    className="cursor-pointer text-xs transition-colors"
                    onClick={() => toggleCategory(cat)}
                  >
                    {cat}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Account Filter */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground">계좌/카드</label>
              <div className="flex flex-wrap gap-1.5">
                {allAccounts.map((acc) => (
                  <Badge
                    key={acc}
                    variant={selectedAccounts.includes(acc) ? "default" : "outline"}
                    className="cursor-pointer text-xs transition-colors"
                    onClick={() => toggleAccount(acc)}
                  >
                    {acc}
                  </Badge>
                ))}
              </div>
            </div>
          </Card>
        )}

        {/* Active filter tags */}
        {activeFilterCount > 0 && !showFilters && (
          <div className="flex flex-wrap gap-1.5">
            {selectedCategories.map((cat) => (
              <Badge key={cat} variant="secondary" className="text-xs gap-1">
                {cat}
                <X className="h-3 w-3 cursor-pointer" onClick={() => toggleCategory(cat)} />
              </Badge>
            ))}
            {selectedAccounts.map((acc) => (
              <Badge key={acc} variant="secondary" className="text-xs gap-1">
                {acc}
                <X className="h-3 w-3 cursor-pointer" onClick={() => toggleAccount(acc)} />
              </Badge>
            ))}
            {dateFrom && (
              <Badge variant="secondary" className="text-xs gap-1">
                시작: {dateFrom}
                <X className="h-3 w-3 cursor-pointer" onClick={() => setDateFrom("")} />
              </Badge>
            )}
            {dateTo && (
              <Badge variant="secondary" className="text-xs gap-1">
                종료: {dateTo}
                <X className="h-3 w-3 cursor-pointer" onClick={() => setDateTo("")} />
              </Badge>
            )}
          </div>
        )}

        {/* Result count */}
        <div className="text-xs text-muted-foreground">
          총 {filtered.length}건
        </div>

        {/* Transaction List */}
        <Card className="glass-card divide-y divide-border">
          {filtered.map((tx) => {
            const catIcon = getCategoryIcon(tx.category);
            const Icon = catIcon.icon;
            const isEditing = editingId === tx.id;

            return (
              <div
                key={tx.id}
                className="px-5 py-3.5 flex items-center justify-between hover:bg-muted/30 transition-colors"
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div className={cn("h-9 w-9 rounded-lg flex items-center justify-center flex-shrink-0", catIcon.color)}>
                    <Icon className={cn("h-4 w-4", catIcon.iconColor)} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">{tx.description}</p>
                    <div className="flex items-center gap-1.5">
                      {isEditing ? (
                        <div className="flex items-center gap-1">
                          <Select value={editCategory} onValueChange={setEditCategory}>
                            <SelectTrigger className="h-6 text-[11px] w-24 border-primary">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {allCategories.map((cat) => (
                                <SelectItem key={cat} value={cat} className="text-xs">
                                  {cat}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <button
                            onClick={() => saveCategory(tx.id)}
                            className="h-5 w-5 rounded flex items-center justify-center text-primary hover:bg-primary/10 transition-colors"
                          >
                            <Check className="h-3 w-3" />
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="h-5 w-5 rounded flex items-center justify-center text-muted-foreground hover:bg-muted transition-colors"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => startEditCategory(tx.id, tx.category)}
                          className="group flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                        >
                          {tx.category}
                          <Pencil className="h-2.5 w-2.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </button>
                      )}
                      <span className="text-xs text-muted-foreground">· {tx.account}</span>
                    </div>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className={cn(
                    "text-sm font-mono font-semibold",
                    tx.type === "income" && "text-income",
                    tx.type === "transfer" && "text-muted-foreground",
                  )}>
                    {tx.amount > 0 ? "+" : "-"}{formatKRWFull(tx.amount)}
                  </p>
                  <p className="text-[10px] text-muted-foreground">{tx.date}</p>
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && (
            <div className="p-12 text-center text-muted-foreground text-sm">
              검색 결과가 없습니다
            </div>
          )}
        </Card>
      </div>
    </AppLayout>
  );
}
