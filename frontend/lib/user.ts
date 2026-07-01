/**
 * Hardcoded demo user. Stands in for real auth/profile, which is a future plan
 * (see CLAUDE.md — auth/role gating lands in each surface's layout later).
 * Phone/name satisfy core/ validation so this profile can prefill checkout.
 */

export interface SavedAddress {
  id: string;
  label: string;
  line: string;
  isDefault?: boolean;
}

export interface UserProfile {
  name: string;
  phone: string;
  email: string;
  initials: string;
  memberSince: string;
  addresses: SavedAddress[];
  stats: { orders: number; favourite: string };
}

export const CURRENT_USER: UserProfile = {
  name: "Aarav Sharma",
  phone: "9876543210",
  email: "aarav.sharma@example.com",
  initials: "AS",
  memberSince: "March 2025",
  addresses: [
    {
      id: "home",
      label: "Home",
      line: "D-42, New Ashok Nagar, New Delhi 110096",
      isDefault: true,
    },
    {
      id: "work",
      label: "Work",
      line: "Tower B, DLF Cyber Hub, Gurugram 122002",
    },
  ],
  stats: { orders: 27, favourite: "BBQ Chicken" },
};
