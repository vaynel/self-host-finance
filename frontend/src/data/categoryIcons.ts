import {
  Briefcase,
  Coffee,
  ShoppingBag,
  Home,
  Bus,
  UtensilsCrossed,
  Tv,
  Dumbbell,
  Apple,
  Store,
  PiggyBank,
  TrendingUp,
  Banknote,
  CreditCard,
  Landmark,
  Building2,
  type LucideIcon,
} from "lucide-react";

export interface IconConfig {
  icon: LucideIcon;
  color: string;       // bg class using semantic tokens
  iconColor: string;   // text class using semantic tokens
}

// 거래 카테고리 아이콘
export const categoryIcons: Record<string, IconConfig> = {
  급여:     { icon: Briefcase,         color: "bg-accent",           iconColor: "text-accent-foreground" },
  카페:     { icon: Coffee,            color: "bg-warning/15",       iconColor: "text-warning" },
  쇼핑:     { icon: ShoppingBag,       color: "bg-primary/15",       iconColor: "text-primary" },
  주거:     { icon: Home,              color: "bg-destructive/10",   iconColor: "text-destructive" },
  교통:     { icon: Bus,               color: "bg-secondary",        iconColor: "text-muted-foreground" },
  배달:     { icon: UtensilsCrossed,   color: "bg-warning/15",       iconColor: "text-warning" },
  구독:     { icon: Tv,                color: "bg-primary/10",       iconColor: "text-primary" },
  운동:     { icon: Dumbbell,          color: "bg-accent",           iconColor: "text-accent-foreground" },
  식료품:   { icon: Apple,             color: "bg-success/15",       iconColor: "text-success" },
  편의점:   { icon: Store,             color: "bg-secondary",        iconColor: "text-muted-foreground" },
  저축:     { icon: PiggyBank,         color: "bg-primary/15",       iconColor: "text-primary" },
  배당:     { icon: TrendingUp,        color: "bg-accent",           iconColor: "text-accent-foreground" },
};

// 금융기관 아이콘
export const institutionIcons: Record<string, IconConfig> = {
  "KB국민은행": { icon: Landmark,   color: "bg-warning/15",       iconColor: "text-warning" },
  "신한은행":   { icon: Building2,  color: "bg-primary/15",       iconColor: "text-primary" },
  "신한카드":   { icon: CreditCard, color: "bg-primary/15",       iconColor: "text-primary" },
  "삼성카드":   { icon: CreditCard, color: "bg-accent",           iconColor: "text-accent-foreground" },
  "키움증권":   { icon: TrendingUp, color: "bg-success/15",       iconColor: "text-success" },
};

export const defaultCategoryIcon: IconConfig = {
  icon: Banknote,
  color: "bg-secondary",
  iconColor: "text-muted-foreground",
};

export const defaultInstitutionIcon: IconConfig = {
  icon: Landmark,
  color: "bg-secondary",
  iconColor: "text-muted-foreground",
};

export function getCategoryIcon(category: string): IconConfig {
  return categoryIcons[category] || defaultCategoryIcon;
}

export function getInstitutionIcon(institution: string): IconConfig {
  return institutionIcons[institution] || defaultInstitutionIcon;
}
