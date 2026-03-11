export interface Transaction {
  id: string;
  date: string;
  description: string;
  amount: number;
  type: "income" | "expense" | "transfer";
  category: string;
  account: string;
  memo?: string;
}

export interface Account {
  id: string;
  name: string;
  type: "bank" | "card" | "investment";
  balance: number;
  institution: string;
  lastSync?: string;
}

export interface Investment {
  id: string;
  name: string;
  ticker: string;
  shares: number;
  avgPrice: number;
  currentPrice: number;
  type: "stock" | "etf";
}

export const transactions: Transaction[] = [
  { id: "1", date: "2026-03-11", description: "월급", amount: 4500000, type: "income", category: "급여", account: "국민은행" },
  { id: "2", date: "2026-03-10", description: "스타벅스", amount: -6500, type: "expense", category: "카페", account: "신한카드" },
  { id: "3", date: "2026-03-10", description: "쿠팡", amount: -45000, type: "expense", category: "쇼핑", account: "삼성카드" },
  { id: "4", date: "2026-03-09", description: "넷플릭스", amount: -17000, type: "expense", category: "구독", account: "신한카드" },
  { id: "5", date: "2026-03-09", description: "GS편의점", amount: -3200, type: "expense", category: "편의점", account: "신한카드" },
  { id: "6", date: "2026-03-08", description: "월세", amount: -700000, type: "expense", category: "주거", account: "국민은행" },
  { id: "7", date: "2026-03-08", description: "배달의민족", amount: -28000, type: "expense", category: "배달", account: "삼성카드" },
  { id: "8", date: "2026-03-07", description: "교통비(티머니)", amount: -55000, type: "expense", category: "교통", account: "국민은행" },
  { id: "9", date: "2026-03-06", description: "삼성전자 배당", amount: 35000, type: "income", category: "배당", account: "키움증권" },
  { id: "10", date: "2026-03-05", description: "적금 이체", amount: -500000, type: "transfer", category: "저축", account: "국민은행" },
  { id: "11", date: "2026-03-04", description: "마켓컬리", amount: -67000, type: "expense", category: "식료품", account: "신한카드" },
  { id: "12", date: "2026-03-03", description: "헬스장", amount: -99000, type: "expense", category: "운동", account: "삼성카드" },
];

export const accounts: Account[] = [
  { id: "1", name: "국민은행 주거래", type: "bank", balance: 8500000, institution: "KB국민은행", lastSync: "2026-03-11" },
  { id: "2", name: "신한 적금", type: "bank", balance: 12000000, institution: "신한은행", lastSync: "2026-03-11" },
  { id: "3", name: "신한카드", type: "card", balance: -450000, institution: "신한카드", lastSync: "2026-03-11" },
  { id: "4", name: "삼성카드", type: "card", balance: -230000, institution: "삼성카드", lastSync: "2026-03-10" },
  { id: "5", name: "키움증권", type: "investment", balance: 15800000, institution: "키움증권", lastSync: "2026-03-11" },
];

export const investments: Investment[] = [
  { id: "1", name: "삼성전자", ticker: "005930", shares: 50, avgPrice: 58000, currentPrice: 62000, type: "stock" },
  { id: "2", name: "KODEX 200", ticker: "069500", shares: 30, avgPrice: 35000, currentPrice: 37500, type: "etf" },
  { id: "3", name: "카카오", ticker: "035720", shares: 20, avgPrice: 52000, currentPrice: 48000, type: "stock" },
  { id: "4", name: "TIGER 미국S&P500", ticker: "360750", shares: 100, avgPrice: 14500, currentPrice: 16200, type: "etf" },
  { id: "5", name: "네이버", ticker: "035420", shares: 15, avgPrice: 195000, currentPrice: 210000, type: "stock" },
];

export const monthlySpending = [
  { month: "10월", income: 4500000, expense: 2800000 },
  { month: "11월", income: 4500000, expense: 3100000 },
  { month: "12월", income: 5200000, expense: 3800000 },
  { month: "1월", income: 4500000, expense: 2600000 },
  { month: "2월", income: 4500000, expense: 2900000 },
  { month: "3월", income: 4535000, expense: 1470700 },
];

export const categorySpending = [
  { name: "주거", value: 700000, color: "hsl(172, 66%, 40%)" },
  { name: "저축", value: 500000, color: "hsl(38, 92%, 50%)" },
  { name: "운동", value: 99000, color: "hsl(262, 60%, 55%)" },
  { name: "식료품", value: 67000, color: "hsl(152, 60%, 42%)" },
  { name: "교통", value: 55000, color: "hsl(200, 60%, 50%)" },
  { name: "쇼핑", value: 45000, color: "hsl(340, 60%, 55%)" },
  { name: "배달", value: 28000, color: "hsl(20, 70%, 55%)" },
  { name: "구독", value: 17000, color: "hsl(280, 50%, 55%)" },
  { name: "카페", value: 6500, color: "hsl(30, 60%, 50%)" },
  { name: "편의점", value: 3200, color: "hsl(100, 40%, 50%)" },
];
