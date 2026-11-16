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
  timer_seconds: number;
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

export type TimerState = { seconds: number; running: boolean; remaining: number };

export type Live = {
  game: Game;
  current_round: number;
  current_question: number;
  standings_hidden: boolean;
  standings: Standing[];
  timer: TimerState;
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

export type TeamListItem = TeamBrief & { members: number };

export type Registration = {
  id: number;
  team: TeamBrief;
  status: "pending" | "approved" | "waitlist" | "rejected" | "withdrawn";
  table_number: number | null;
  created_at: string;
};

export type GameCell = { points: number; rating_j: number; place: number | null; eligible: boolean };

export type StandingRow = {
  place: number | null;
  team: TeamBrief;
  points: number;
  rating_j: number;
  tie_group: number | null;
  prev_place: number | null;
  by_game: Record<string, GameCell>;
  other_points: number;
  played: number;
  wins: number;
  best: number;
};

export type SeasonStandings = {
  season: { id: number; name: string };
  games: { id: number; title: string; starts_at: string }[];
  rows: StandingRow[];
};

export const TEAM_STATUS: Record<string, string> = {
  draft: "Qoralama",
  pending: "Tasdiq kutilmoqda",
  active: "Faol",
  withdrawn: "Chiqib ketgan",
  disqualified: "Chetlatilgan",
};

export const REG_STATUS: Record<Registration["status"], string> = {
  pending: "Ko'rib chiqilmoqda",
  approved: "Tasdiqlangan",
  waitlist: "Navbatda",
  rejected: "Rad etilgan",
  withdrawn: "Bekor qilingan",
};

// ---------------------------------------------------------------- Kitobxonlik

export type Book = { id: number; title: string; author: string; description: string; cover: string | null };

export type RoundStatus = "draft" | "voting" | "reading" | "grading" | "done";

export type ReadingRound = {
  id: number;
  title: string;
  status: RoundStatus;
  candidates: Book[];
  vote_ends: string | null;
  votes: Record<string, number> | null;
  my_vote: number | null;
  selected_book: Book | null;
  reading_days: number;
  reading_starts: string | null;
  my_deadline: string | null;
  min_review_length: number;
  criteria: { id: number; name: string; max_points: number }[];
  my_review: { id: number; status: string; submitted_at: string; text: string; has_file: boolean } | null;
  can_read: boolean;
};

export type ReviewForGrading = {
  id: number;
  author: { id: number; name: string };
  text: string;
  has_file: boolean;
  submitted_at: string;
  status: "submitted" | "approved";
  grades_count: number;
  average: string | null;
  my_grade: { comment: string; total: number; scores: Record<string, number> } | null;
};

export type LeaderRow = { place: number; user: { id: number; name: string; branch: string | null }; points: number };

export const ROUND_STATUS: Record<RoundStatus, string> = {
  draft: "Qoralama",
  voting: "Ovoz berish",
  reading: "O'qish",
  grading: "Baholash",
  done: "Yakunlangan",
};

// ---------------------------------------------------------------- Savollar banki

export type QuestionStatus = "draft" | "editing" | "approved" | "used";

export type Question = {
  id: number;
  text: string;
  answer: string;
  accepted_answers: string;
  comment: string;
  source: string;
  topic: string;
  difficulty: number | null;
  status: QuestionStatus;
  author: string | null;
  created_at: string;
  assigned: { game: number; game_title: string; number: number } | null;
};

export type QuestionBank = { topics: string[]; counts: Record<QuestionStatus, number>; items: Question[] };

export type GameQuestionSlot = { number: number; round: number; question: Question | null };

export const QUESTION_STATUS: Record<QuestionStatus, string> = {
  draft: "Qoralama",
  editing: "Tahrirda",
  approved: "Tasdiqlangan",
  used: "Ishlatilgan",
};

// ---------------------------------------------------------------- E'lonlar

export type Announcement = {
  id: number;
  title: string;
  body: string;
  module: "core" | "zakovat" | "kitobxonlik" | "munozara" | "sport";
  pinned: boolean;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
  author: string | null;
  can_edit: boolean;
};

export type AnnouncementList = { can_post: Announcement["module"][]; items: Announcement[] };

export const MODULE_LABEL: Record<Announcement["module"], string> = {
  core: "Umumiy",
  zakovat: "Zakovat",
  kitobxonlik: "Kitobxonlik",
  munozara: "Munozara",
  sport: "Sport",
};
