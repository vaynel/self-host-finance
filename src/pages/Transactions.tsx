import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { transactions } from "@/data/mockData";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { getCategoryIcon } from "@/data/categoryIcons";

function formatKRWFull(value: number) {
  return `₩${Math.abs(value).toLocaleString()}`;
}

type FilterType = "all" | "income" | "expense" | "transfer";

export default function Transactions() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterType>("all");

  const filtered = transactions.filter((tx) => {
    const matchSearch = tx.description.toLowerCase().includes(search.toLowerCase()) ||
      tx.category.toLowerCase().includes(search.toLowerCase());
    const matchFilter = filter === "all" || tx.type === filter;
    return matchSearch && matchFilter;
  });

  const filters: { label: string; value: FilterType }[] = [
    { label: "전체", value: "all" },
    { label: "수입", value: "income" },
    { label: "지출", value: "expense" },
    { label: "이체", value: "transfer" },
  ];

  return (
    <AppLayout title="거래 내역">
      <div className="space-y-4 max-w-4xl">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="거래 검색..."
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
          </div>
        </div>

        <Card className="glass-card divide-y divide-border">
          {filtered.map((tx) => {
            const catIcon = getCategoryIcon(tx.category);
            const Icon = catIcon.icon;
            return (
              <div key={tx.id} className="px-5 py-3.5 flex items-center justify-between hover:bg-muted/30 transition-colors cursor-pointer">
                <div className="flex items-center gap-3">
                  <div className={cn("h-9 w-9 rounded-lg flex items-center justify-center", catIcon.color)}>
                    <Icon className={cn("h-4 w-4", catIcon.iconColor)} />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{tx.description}</p>
                    <p className="text-xs text-muted-foreground">{tx.category} · {tx.account}</p>
                  </div>
                </div>
                <div className="text-right">
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
