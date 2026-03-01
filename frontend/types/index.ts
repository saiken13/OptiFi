export interface User {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  auth_provider: string;
  created_at: string;
}

export interface Goal {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  target_amount: number;
  current_amount: number;
  monthly_contribution: number;
  target_date: string | null;
  status: "active" | "completed" | "paused";
  priority: number;
  created_at: string;
}

export interface Budget {
  id: string;
  user_id: string;
  category: string;
  monthly_limit: number;
  spent_this_month: number;
  month: number;
  year: number;
  created_at: string;
}

export interface Transaction {
  id: string;
  user_id: string;
  date: string;
  description: string;
  amount: number;
  category: string | null;
  merchant: string | null;
  account: string | null;
  created_at: string;
}

export interface Loan {
  id: string;
  user_id: string;
  name: string;
  loan_type: string;
  principal: number;
  current_balance: number;
  interest_rate: number;
  monthly_payment: number;
  extra_payment: number;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
}

export interface Alert {
  id: string;
  user_id: string;
  alert_type: string;
  title: string;
  message: string;
  is_read: boolean;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface CardRewardRule {
  id: string;
  card_id: string;
  rule_type: string;
  category: string;
  reward_rate: number;
  cap_amount: number | null;
  cap_period: string | null;
  merchant_match: string | null;
  activation_required: boolean;
  evidence: string | null;
  source_url: string | null;
  created_at: string;
}

export interface Card {
  id: string;
  user_id: string;
  name: string;
  issuer: string;
  last_four: string | null;
  network: string | null;
  annual_fee: number;
  is_active: boolean;
  reward_rules: CardRewardRule[];
  created_at: string;
}

export interface Membership {
  id: string;
  user_id: string;
  name: string;
  merchant: string;
  annual_fee: number;
  benefits: Record<string, unknown> | null;
  is_active: boolean;
  renewal_date: string | null;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent_type: string | null;
  structured_data: Record<string, unknown> | null;
  created_at: string;
}

export interface CardOption {
  card_name: string;
  cashback_rate: number;
  cashback_amount: number;
}

export interface OptimizedOption {
  rank: number;
  merchant: string;
  price: number;
  shipping: number;
  shipping_after_membership: number;
  membership_savings: number;
  membership_name: string | null;
  best_card_id: string | null;
  best_card_name: string | null;
  cashback_rate: number;
  cashback_amount: number;
  net_cost: number;
  total_savings: number;
  url: string;
  evidence: string | null;
  card_options?: CardOption[];
}

export interface PurchaseOptimizeResult {
  query: string;
  best_option: OptimizedOption;
  alternatives: OptimizedOption[];
  all_options: OptimizedOption[];
}

export type AgentIntent =
  | "budget"
  | "goal"
  | "loan"
  | "tax"
  | "weekly_review"
  | "purchase_optimize"
  | "card_import"
  | "general";
