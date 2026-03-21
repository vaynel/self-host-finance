/**
 * API 클라이언트 설정 및 API 호출 함수들
 */

// 같은 서버에 있으므로 상대 경로 사용 (Vite 프록시를 통해 내부 통신)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/v1";

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: {
    code: number;
    message: string;
    details?: any[];
  } | null;
  meta?: {
    page?: number;
    limit?: number;
    total?: number;
  };
}

/**
 * API 요청 헤더 생성
 */
function getHeaders(): HeadersInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  const token = localStorage.getItem("finflow_access_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

/**
 * API 요청 래퍼 함수
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getHeaders(),
      ...options.headers,
    },
  });

  const data = await response.json();

  if (!response.ok) {
    const baseMessage = data.error?.message || `API 요청 실패: ${response.status}`;
    const details = data.error?.details;
    if (details && Array.isArray(details) && details.length > 0) {
      return Promise.reject(new Error(`${baseMessage} (details: ${JSON.stringify(details)})`));
    }
    throw new Error(baseMessage);
  }

  return data;
}

// ==================== 인증 API ====================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  user: {
    id: string;
    email: string;
    name: string;
  };
}

export const authApi = {
  login: async (req: LoginRequest): Promise<ApiResponse<AuthResponse>> => {
    return apiRequest<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(req),
    });
  },

  register: async (req: RegisterRequest): Promise<ApiResponse<AuthResponse>> => {
    return apiRequest<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(req),
    });
  },

  refresh: async (refreshToken: string): Promise<ApiResponse<AuthResponse>> => {
    return apiRequest<AuthResponse>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refreshToken }),
    });
  },

  logout: async (): Promise<ApiResponse<{ message: string }>> => {
    return apiRequest<{ message: string }>("/auth/logout", {
      method: "POST",
    });
  },
};

// ==================== 거래 내역 API ====================

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

export interface TransactionCreate {
  date: string;
  description: string;
  amount: number;
  type: "income" | "expense" | "transfer";
  category: string;
  account: string;
  memo?: string;
}

export interface TransactionUpdate extends Partial<TransactionCreate> {}

export interface TransactionListParams {
  page?: number;
  limit?: number;
  type?: "income" | "expense" | "transfer";
  category?: string;
  account?: string;
  startDate?: string;
  endDate?: string;
  search?: string;
}

export const transactionsApi = {
  list: async (params?: TransactionListParams): Promise<ApiResponse<Transaction[]>> => {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value));
        }
      });
    }
    const query = queryParams.toString();
    return apiRequest<Transaction[]>(`/transactions${query ? `?${query}` : ""}`);
  },

  get: async (id: string): Promise<ApiResponse<Transaction>> => {
    return apiRequest<Transaction>(`/transactions/${id}`);
  },

  create: async (data: TransactionCreate): Promise<ApiResponse<Transaction>> => {
    return apiRequest<Transaction>("/transactions", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  update: async (id: string, data: TransactionUpdate): Promise<ApiResponse<Transaction>> => {
    return apiRequest<Transaction>(`/transactions/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  delete: async (id: string): Promise<ApiResponse<void>> => {
    return apiRequest<void>(`/transactions/${id}`, {
      method: "DELETE",
    });
  },
};

// ==================== 계좌 API ====================

export interface Account {
  id: string;
  name: string;
  type: "bank" | "investment";
  balance: number;
  institution: string;
  account_number?: string;
  lastSync?: string;
}

export interface AccountCreate {
  name: string;
  type: "bank" | "investment";
  balance: number;
  institution: string;
  account_number?: string;
}

export interface AccountUpdate extends Partial<AccountCreate> {}

export interface AccountFlow {
  accountId: string;
  chartData: Array<{
    date: string;
    balance: number;
  }>;
}

export const accountsApi = {
  list: async (): Promise<ApiResponse<Account[]>> => {
    return apiRequest<Account[]>("/accounts");
  },

  get: async (id: string): Promise<ApiResponse<Account>> => {
    return apiRequest<Account>(`/accounts/${id}`);
  },

  create: async (data: AccountCreate): Promise<ApiResponse<Account>> => {
    return apiRequest<Account>("/accounts", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  update: async (id: string, data: AccountUpdate): Promise<ApiResponse<Account>> => {
    return apiRequest<Account>(`/accounts/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  delete: async (id: string): Promise<ApiResponse<void>> => {
    return apiRequest<void>(`/accounts/${id}`, {
      method: "DELETE",
    });
  },

  getFlow: async (id: string, period?: string): Promise<ApiResponse<AccountFlow>> => {
    const query = period ? `?period=${period}` : "";
    return apiRequest<AccountFlow>(`/accounts/${id}/flow${query}`);
  },
};

// ==================== 투자 API ====================

export interface InvestmentHolding {
  ticker: string;
  name: string;
  type: string;
  shares: number;
  avgPrice: number;
  currentPrice: number;
  totalValue: number;
  profitLoss: number;
  profitLossRate: number;
  source?: "snapshot" | "trade_fallback";
  accountId?: string;
}

export interface InvestmentTrade {
  id: string;
  ticker: string;
  name: string;
  action: "buy" | "sell";
  date: string;
  shares: number;
  price: number;
  fee?: number;
}

export interface InvestmentTradeCreate {
  ticker: string;
  action: "buy" | "sell";
  date: string;
  shares: number;
  price: number;
  fee?: number;
  accountId?: string;
}

export interface InvestmentPrice {
  ticker: string;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface InvestmentListParams {
  ticker?: string;
  action?: "buy" | "sell";
  startDate?: string;
  endDate?: string;
}

export interface InvestmentOrder {
  id: string;
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  price?: number | null;
  order_type: "limit" | "market";
  broker_order_id?: string | null;
  status: "pending" | "partially_filled" | "filled" | "cancelled" | "rejected" | "unknown";
  requested_at: string;
  filled_at?: string | null;
}

export interface InvestmentExecution {
  id: string;
  broker_execution_id?: string | null;
  executed_quantity: number;
  executed_price: number;
  fee?: number | null;
  executed_at: string;
  settled: "no" | "yes" | "error";
  settled_at?: string | null;
}

export interface InvestmentOrderDetail extends InvestmentOrder {
  executions: InvestmentExecution[];
}

export interface InvestmentOrderCreate {
  account_id: string;
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  price?: number;
  order_type?: "limit" | "market";
}

export interface AutoTradeRule {
  id: string;
  account_id: string;
  ticker: string;
  side: "buy" | "sell";
  enabled: boolean;
  target_price?: number | null;
  stop_price?: number | null;
  order_type: "limit" | "market";
  quantity: number;
  limit_price?: number | null;
  cooldown_seconds: number;
  last_triggered_at?: string | null;
  trigger_kind: "cost_drop" | "peak_drop";
  trigger_percent: number;
  action_mode: "alert_only" | "auto_sell" | "alert_and_sell";
}

export interface AutoTradeRuleCreate {
  account_id: string;
  ticker: string;
  side: "buy" | "sell";
  enabled?: boolean;
  target_price?: number;
  stop_price?: number;
  order_type?: "limit" | "market";
  quantity: number;
  limit_price?: number;
  cooldown_seconds?: number;
  trigger_kind?: "cost_drop" | "peak_drop";
  trigger_percent?: number;
  action_mode?: "alert_only" | "auto_sell" | "alert_and_sell";
}

export interface AutoTradeRuleUpdate extends Partial<AutoTradeRuleCreate> {}

export interface AutoTradeGlobalRule {
  id: string;
  account_id: string;
  enabled: boolean;
  trigger_kind: "cost_drop" | "peak_drop";
  trigger_percent: number;
  action_mode: "alert_only" | "auto_sell" | "alert_and_sell";
  order_type: "limit" | "market";
  sell_quantity_ratio: number;
  limit_price?: number | null;
  cooldown_seconds: number;
  last_triggered_at?: string | null;
}

export interface AutoTradeGlobalRuleCreate {
  account_id: string;
  enabled?: boolean;
  trigger_kind?: "cost_drop" | "peak_drop";
  trigger_percent?: number;
  action_mode?: "alert_only" | "auto_sell" | "alert_and_sell";
  order_type?: "limit" | "market";
  sell_quantity_ratio?: number;
  limit_price?: number | null;
  cooldown_seconds?: number;
}

export interface AutoTradeGlobalRuleUpdate {
  enabled?: boolean;
  trigger_kind?: "cost_drop" | "peak_drop";
  trigger_percent?: number;
  action_mode?: "alert_only" | "auto_sell" | "alert_and_sell";
  order_type?: "limit" | "market";
  sell_quantity_ratio?: number;
  limit_price?: number | null;
  cooldown_seconds?: number;
}

export interface KISConnectRequest {
  broker_account_no: string; // CANO 또는 10자리 연속번호(뒤 2자리를 상품 힌트로 사용)
  /** 비우면 서버가 잔고조회로 ACNT_PRDT_CD 자동 탐색 */
  product_code?: string | null;
  is_mock?: boolean;
}

export interface KISConnectResponse {
  account_id: string;
  broker_account_id: string;
  broker_type: string;
  api_enabled: boolean;
  order_enabled: boolean;
  is_mock: boolean;
  token_expires_at?: string | null;
  cano?: string;
  resolved_product_code?: string;
  product_code_auto?: boolean;
}

export const investmentsApi = {
  getHoldings: async (): Promise<ApiResponse<InvestmentHolding[]>> => {
    return apiRequest<InvestmentHolding[]>("/investments/holdings");
  },

  getTrades: async (params?: InvestmentListParams): Promise<ApiResponse<InvestmentTrade[]>> => {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value));
        }
      });
    }
    const query = queryParams.toString();
    return apiRequest<InvestmentTrade[]>(`/investments/trades${query ? `?${query}` : ""}`);
  },

  getPrices: async (ticker: string, period?: string): Promise<ApiResponse<InvestmentPrice[]>> => {
    const query = period ? `?period=${period}` : "";
    return apiRequest<InvestmentPrice[]>(`/investments/prices/${ticker}${query}`);
  },

  createTrade: async (data: InvestmentTradeCreate): Promise<ApiResponse<InvestmentTrade>> => {
    return apiRequest<InvestmentTrade>("/investments/trades", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  syncAccount: async (accountId: string): Promise<ApiResponse<{
    accountId: string;
    holdingsCount: number;
    cashBalance: number;
    orderableCash: number;
    syncedAt: string;
  }>> => {
    return apiRequest(`/investments/accounts/${accountId}/sync`, {
      method: "POST",
    });
  },

  kisConnect: async (accountId: string, data: KISConnectRequest): Promise<ApiResponse<KISConnectResponse>> => {
    return apiRequest<KISConnectResponse>(`/investments/accounts/${accountId}/kis/connect`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  createOrder: async (data: InvestmentOrderCreate): Promise<ApiResponse<InvestmentOrderDetail>> => {
    return apiRequest<InvestmentOrderDetail>("/investments/orders", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  listOrders: async (params?: {
    account_id?: string;
    status?: InvestmentOrder["status"];
    limit?: number;
  }): Promise<ApiResponse<InvestmentOrder[]>> => {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value));
        }
      });
    }
    const query = queryParams.toString();
    return apiRequest<InvestmentOrder[]>(`/investments/orders${query ? `?${query}` : ""}`);
  },

  getOrder: async (orderId: string): Promise<ApiResponse<InvestmentOrderDetail>> => {
    return apiRequest<InvestmentOrderDetail>(`/investments/orders/${orderId}`);
  },

  refreshOrder: async (orderId: string): Promise<ApiResponse<{
    order: InvestmentOrderDetail;
    new_executions: InvestmentExecution[];
  }>> => {
    return apiRequest(`/investments/orders/${orderId}/refresh`, {
      method: "POST",
    });
  },

  listRules: async (): Promise<ApiResponse<AutoTradeRule[]>> => {
    return apiRequest<AutoTradeRule[]>("/investments/rules");
  },

  createRule: async (data: AutoTradeRuleCreate): Promise<ApiResponse<AutoTradeRule>> => {
    return apiRequest<AutoTradeRule>("/investments/rules", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  updateRule: async (ruleId: string, data: AutoTradeRuleUpdate): Promise<ApiResponse<AutoTradeRule>> => {
    return apiRequest<AutoTradeRule>(`/investments/rules/${ruleId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  deleteRule: async (ruleId: string): Promise<ApiResponse<{ deleted: boolean }>> => {
    return apiRequest<{ deleted: boolean }>(`/investments/rules/${ruleId}`, {
      method: "DELETE",
    });
  },

  listGlobalRules: async (): Promise<ApiResponse<AutoTradeGlobalRule[]>> => {
    return apiRequest<AutoTradeGlobalRule[]>("/investments/rules/global");
  },

  createGlobalRule: async (data: AutoTradeGlobalRuleCreate): Promise<ApiResponse<AutoTradeGlobalRule>> => {
    return apiRequest<AutoTradeGlobalRule>("/investments/rules/global", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  updateGlobalRule: async (
    ruleId: string,
    data: AutoTradeGlobalRuleUpdate,
  ): Promise<ApiResponse<AutoTradeGlobalRule>> => {
    return apiRequest<AutoTradeGlobalRule>(`/investments/rules/global/${ruleId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  deleteGlobalRule: async (ruleId: string): Promise<ApiResponse<{ deleted: boolean }>> => {
    return apiRequest<{ deleted: boolean }>(`/investments/rules/global/${ruleId}`, {
      method: "DELETE",
    });
  },

  listRuleLogs: async (limit = 50): Promise<ApiResponse<Array<{
    id: string;
    rule_id: string;
    account_id: string;
    ticker: string;
    status: "skipped" | "triggered" | "failed";
    reason?: string | null;
    order_id?: string | null;
    created_at: string;
  }>>> => {
    const query = `?limit=${limit}`;
    return apiRequest(`/investments/rules/logs${query}`);
  },

  listRuleTriggers: async (): Promise<ApiResponse<Array<{
    rule: {
      id: string;
      account_id: string;
      ticker?: string;
      trigger_kind: "cost_drop" | "peak_drop";
      trigger_percent: number;
      action_mode: "alert_only" | "auto_sell" | "alert_and_sell";
    };
    ticker: string;
    name: string;
    currentPrice: number;
    shares: number;
    threshold: number;
    actual: number;
  }>>> => {
    return apiRequest(`/investments/rules/triggers`);
  },

  enableAutoTrade: async (accountId: string): Promise<ApiResponse<{ account_id: string; auto_trade_enabled: boolean }>> => {
    return apiRequest(`/investments/accounts/${accountId}/auto-trade/enable`, {
      method: "POST",
    });
  },

  disableAutoTrade: async (accountId: string): Promise<ApiResponse<{ account_id: string; auto_trade_enabled: boolean }>> => {
    return apiRequest(`/investments/accounts/${accountId}/auto-trade/disable`, {
      method: "POST",
    });
  },
};

// ==================== 리포트 API ====================

export interface MonthlySummary {
  month: string;
  income: number;
  expense: number;
  savings: number;
  savingsRate: number;
}

/** 백엔드는 `category`·`amount`로 내려줄 수 있음 */
export interface CategorySpending {
  name?: string;
  category?: string;
  value?: number;
  amount?: number;
  color?: string;
}

export const reportsApi = {
  getMonthlySummary: async (year?: number): Promise<ApiResponse<MonthlySummary[]>> => {
    const query = year ? `?year=${year}` : "";
    return apiRequest<MonthlySummary[]>(`/reports/monthly-summary${query}`);
  },

  getCategorySpending: async (month?: string): Promise<ApiResponse<CategorySpending[]>> => {
    const query = month ? `?month=${month}` : "";
    return apiRequest<CategorySpending[]>(`/reports/category-spending${query}`);
  },
};

// ==================== 업로드 API ====================

export interface UploadResult {
  imported: number;
  skipped: number;
  duplicates?: number;
  errors: Array<{ row: number; message: string }>;
  column_mapping?: Record<string, number | null>;
}

export interface PreviewRow {
  row: number;
  date: string;
  description: string;
  amount: number;
  type: string;
  category: string;
  account: string;
  memo: string;
}

export interface PreviewResult {
  rows: PreviewRow[];
  column_mapping?: Record<string, number | null>;
  total: number;
}

export const uploadApi = {
  preview: async (
    file: File,
    format?: string,
    accountId?: string
  ): Promise<ApiResponse<PreviewResult>> => {
    const formData = new FormData();
    formData.append("file", file);
    if (format) {
      formData.append("format", format);
    }
    if (accountId) {
      formData.append("accountId", accountId);
    }

    const token = localStorage.getItem("finflow_access_token");
    const headers: HeadersInit = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}/upload/preview`, {
      method: "POST",
      headers,
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error?.message || `미리보기 실패: ${response.status}`);
    }

    return data;
  },

  uploadTransactions: async (
    file: File,
    accountId: string,
    format?: string,
    skipDuplicates: boolean = true,
    toleranceDays: number = 0
  ): Promise<ApiResponse<UploadResult>> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("accountId", accountId);
    if (format) {
      formData.append("format", format);
    }
    formData.append("skipDuplicates", skipDuplicates.toString());
    if (toleranceDays > 0) {
      formData.append("toleranceDays", toleranceDays.toString());
    }

    const token = localStorage.getItem("finflow_access_token");
    const headers: HeadersInit = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}/upload/transactions`, {
      method: "POST",
      headers,
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error?.message || `업로드 실패: ${response.status}`);
    }

    return data;
  },
};

// ==================== 설정 API ====================

export interface UserSettings {
  currency: string;
  language: string;
  notifications?: Record<string, any>;
  discord_webhook_configured: boolean;
  discord_webhook_masked: string | null;
}

/** PUT /settings 본문(웹훅은 빈 문자열로 삭제) */
export type UserSettingsUpdate = Partial<
  Pick<UserSettings, "currency" | "language" | "notifications">
> & {
  discord_webhook_url?: string;
};

export const settingsApi = {
  get: async (): Promise<ApiResponse<UserSettings>> => {
    return apiRequest<UserSettings>("/settings");
  },

  update: async (data: UserSettingsUpdate): Promise<ApiResponse<UserSettings>> => {
    return apiRequest<UserSettings>("/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },
};

// ==================== 카테고리 키워드 API ====================

export interface CategoryKeyword {
  id: string;
  keyword: string;
  priority: "high" | "normal" | "low";
  created_at?: string;
}

export interface CategoryKeywordsByCategory {
  [category: string]: CategoryKeyword[];
}

export const categoryKeywordsApi = {
  list: async (category?: string): Promise<ApiResponse<CategoryKeywordsByCategory>> => {
    const query = category ? `?category=${encodeURIComponent(category)}` : "";
    return apiRequest<CategoryKeywordsByCategory>(`/category-keywords${query}`);
  },

  create: async (data: {
    category: string;
    keyword: string;
    priority?: "high" | "normal" | "low";
  }): Promise<ApiResponse<CategoryKeyword>> => {
    return apiRequest<CategoryKeyword>("/category-keywords", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  update: async (
    keywordId: string,
    data: Partial<{
      category: string;
      keyword: string;
      priority: "high" | "normal" | "low";
    }>
  ): Promise<ApiResponse<CategoryKeyword>> => {
    return apiRequest<CategoryKeyword>(`/category-keywords/${keywordId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  delete: async (keywordId: string): Promise<ApiResponse<{ message: string }>> => {
    return apiRequest<{ message: string }>(`/category-keywords/${keywordId}`, {
      method: "DELETE",
    });
  },

  listCategories: async (): Promise<ApiResponse<string[]>> => {
    return apiRequest<string[]>("/category-keywords/categories");
  },
};
