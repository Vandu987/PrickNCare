// ── User ──
export interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  role: "admin" | "client" | "phlebotomist" | "manager";
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Client ──
export interface Client {
  id: number;
  user: User;
  company_name: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  gst_number?: string;
  contact_person: string;
  contact_phone: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Package / Test ──
export interface Package {
  id: number;
  name: string;
  description: string;
  price: number;
  tests_included: string[];
  tube_type: string;
  sample_type: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Order ──
export type OrderStatus =
  | "pending"
  | "confirmed"
  | "assigned"
  | "in_progress"
  | "sample_collected"
  | "completed"
  | "cancelled";

export interface OrderPatient {
  id: number;
  name: string;
  age: number;
  gender: "M" | "F" | "O";
  phone: string;
  packages: Package[];
}

export interface Order {
  id: number;
  order_number: string;
  client: Client;
  patients: OrderPatient[];
  status: OrderStatus;
  scheduled_date: string;
  scheduled_time_slot: string;
  collection_address: string;
  city: string;
  pincode: string;
  notes?: string;
  assigned_phlebotomist?: User;
  priority: "normal" | "high";
  total_amount: number;
  created_at: string;
  updated_at: string;
}

// ── API Response Wrappers ──
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiError {
  detail: string;
  code?: string;
}
