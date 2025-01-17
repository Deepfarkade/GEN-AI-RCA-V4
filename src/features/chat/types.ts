interface TableData {
  records: Record<string, any>[]; // Array of records with dynamic keys
  columns: string[]; // List of column names
}

export interface Message {
  id: string;
  text: string;
  content?: string;
  sender: 'user' | 'bot';
  role?: 'user' | 'assistant';
  timestamp: Date;
  sessionId: string;
  response_type: string;
  table_data: TableData| null;
  summary:string|null;
  next_question?:string;
  df_parent?: string; // Optional field for parent DF reference
}

export interface ChatSession {
  id: string;
  title: string;
  lastMessage?: string;
  timestamp: Date;
  messages: Message[];
  user_id: string;
}

export interface ChatState {
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  isLoading: boolean;
  error: string | null;
}

export interface ChatResponse {
  id: string;
  text: string;
  sender: 'bot';
  timestamp: string;
  sessionId: string;
  summary: string|null;
  table_data: TableData| null;
}