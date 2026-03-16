import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string;
  change?: string;
  changeType?: "positive" | "negative" | "neutral";
  icon: LucideIcon;
  iconClassName?: string;
}

export function StatCard({ label, value, change, changeType = "neutral", icon: Icon, iconClassName }: StatCardProps) {
  return (
    <Card className="p-5 glass-card">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <p className="stat-label">{label}</p>
          <p className="stat-value">{value}</p>
          {change && (
            <p className={cn(
              "text-xs font-medium",
              changeType === "positive" && "text-success",
              changeType === "negative" && "text-expense",
              changeType === "neutral" && "text-muted-foreground"
            )}>
              {change}
            </p>
          )}
        </div>
        <div className={cn("h-10 w-10 rounded-xl flex items-center justify-center", iconClassName || "bg-accent")}>
          <Icon className="h-5 w-5 text-accent-foreground" />
        </div>
      </div>
    </Card>
  );
}
