export type Me = {
  id: number;
  name: string;
  status: string;
  is_admin: boolean;
  employee: { full_name: string; branch: string; position: string } | null;
  roles: { role: string; module: string; season: string | null }[];
  season: { name: string; start: string; end: string } | null;
};

export type ZakovatMe = {
  season: { id: number; name: string };
  team: TeamDetail | null;
  is_captain: boolean;
  invitations: { id: number; team: TeamBrief }[];
  is_tg: boolean;
  is_scorer: boolean;
};

export type TeamBrief = { id: number; name: string; status: string };
export type UserBrief = { id: number; name: string; branch: string | null };
export type TeamDetail = TeamBrief & {
  captain: UserBrief;
  members: { id: number; user: UserBrief; status: string }[];
};

export type GameStatus =
  | "planned"
  | "registration"
  | "in_progress"
  | "preliminary"
  | "final"
  | "cancelled";

export type Game = {
  id: number;
  title: string;
  kind: "league" | "tiebreak" | "practice";
  status: GameStatus;
  starts_at: string;
  venue: string;
  max_teams: number | null;
  registration_deadline: string;
  rounds: number;
  questions_per_round: number;
  hide_standings: boolean;
  approved_teams: number;
  my_registration?: { id: number; status: string; table_number: number | null } | null;
};

export type LineupEntry = {
  id: number;
  round_no: number;
  user: UserBrief;
  from_question: number;
};

export type SheetTeam = {
  table_number: number | null;
  team: TeamBrief;
  players: UserBrief[];
  lineup: LineupEntry[];
  answers: (boolean | null)[];
  counted: number[];
  points: number;
  rating_j: number;
  place: number | null;
};

export type Sheet = {
  game: Game;
  current_round: number;
  current_question: number;
  teams: SheetTeam[];
};

export type Standing = {
  place: number | null;
  team: { id: number; name: string };
  points: number;
  rating_j: number;
  eligible: boolean;
};

export type Live = {
  game: Game;
  current_round: number;
  current_question: number;
  standings_hidden: boolean;
  standings: Standing[];
};

export type Appeal = {
  id: number;
  team: TeamBrief;
  number: number;
  content: string;
  evidence: string;
  status: "pending" | "accepted" | "rejected";
  decision_reason: string;
};

export const GAME_STATUS: Record<GameStatus, string> = {
  planned: "Rejalashtirilgan",
  registration: "Ro'yxatdan o'tish",
  in_progress: "O'yin ketmoqda",
  preliminary: "Dastlabki natija",
  final: "Yakuniy natija",
  cancelled: "Bekor qilingan",
};
