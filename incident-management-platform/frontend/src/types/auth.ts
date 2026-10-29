export interface User {
  id: number;
  email: string;
  full_name: string;
  role: "USER" | "TECHNICIAN" | "ADMIN";
  is_active: boolean;
  created_at: string;
}
