import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { accounts } from "@/data/mockData";
import { Landmark, CreditCard, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { getInstitutionIcon } from "@/data/categoryIcons";

const typeConfig = {
  bank: { label: "은행 계좌", icon: Landmark },
  card: { label: "카드", icon: CreditCard },
  investment: { label: "증권 계좌", icon: TrendingUp },
};

function formatKRW(value: number) {
  return `₩${Math.abs(value).toLocaleString()}`;
}

export default function Accounts() {
  const grouped = {
    bank: accounts.filter((a) => a.type === "bank"),
    card: accounts.filter((a) => a.type === "card"),
    investment: accounts.filter((a) => a.type === "investment"),
  };

  return (
    <AppLayout title="계좌 관리">
      <div className="space-y-6 max-w-3xl">
        {(Object.keys(grouped) as Array<keyof typeof grouped>).map((type) => {
          const config = typeConfig[type];
          const items = grouped[type];
          if (items.length === 0) return null;

          const total = items.reduce((s, a) => s + a.balance, 0);

          return (
            <div key={type} className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">{config.label}</h3>
                <span className={cn(
                  "text-sm font-mono font-semibold",
                  total >= 0 ? "text-foreground" : "text-expense"
                )}>
                  {total < 0 ? "-" : ""}{formatKRW(total)}
                </span>
              </div>
              <div className="space-y-2">
                {items.map((account) => {
                  const instIcon = getInstitutionIcon(account.institution);
                  const Icon = instIcon.icon;
                  return (
                    <Card key={account.id} className="p-4 glass-card flex items-center justify-between hover:bg-muted/30 transition-colors cursor-pointer">
                      <div className="flex items-center gap-3">
                        <div className={cn("h-10 w-10 rounded-xl flex items-center justify-center", instIcon.color)}>
                          <Icon className={cn("h-5 w-5", instIcon.iconColor)} />
                        </div>
                        <div>
                          <p className="text-sm font-medium">{account.name}</p>
                          <p className="text-xs text-muted-foreground">{account.institution}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={cn(
                          "text-sm font-mono font-semibold",
                          account.balance < 0 && "text-expense"
                        )}>
                          {account.balance < 0 ? "-" : ""}{formatKRW(account.balance)}
                        </p>
                        {account.lastSync && (
                          <p className="text-[10px] text-muted-foreground">동기화: {account.lastSync}</p>
                        )}
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </AppLayout>
  );
}
