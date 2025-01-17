import { api } from '../../../lib/api';
import { Message, ChatSession } from '../types';

export class ChatService {
  static async sendMessage(content: string, sessionId: string): Promise<Message> {
    try {
      const response = await api.post<Message>(`/chat/${sessionId}/send`, { text: content });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to send message');
    }
  }

  // static async getChatHistory(): Promise<ChatSession[]> {
  //   try {
  //     const response = await api.get<ChatSession[]>('/chat/sessions');
  //     return response.data;
  //   } catch (error: any) {
  //     throw new Error(error.response?.data?.detail || 'Failed to fetch chat history');
  //   }
  // }

  static async getChatHistory(): Promise<ChatSession[]> {
    try {
      const response = await api.get<ChatSession[]>('/chat/sessions'); 
  
      // Apply filtering logic for each session
      const filteredSessions = response.data.map((session) => ({
        ...session,
        messages: session.messages.filter((message: Message) => !message.df_parent),
      }));
  
      return filteredSessions; // Return the filtered sessions
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch chat history');
    }
  }
  

  

  static async createNewChat(): Promise<ChatSession> {
    try {
      const response = await api.post<ChatSession>('/chat/sessions');

      
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to create new chat');
    }
  }

  // static async getSessionMessages(sessionId: string): Promise<Message[]> {
  //   try {
  //     const response = await api.get<Message[]>(`/chat/${sessionId}/messages`);
  //     return response.data;
  //   } catch (error: any) {
  //     throw new Error(error.response?.data?.detail || 'Failed to fetch session messages');
  //   }
  // }

  // static async getSessionMessages(sessionId: string): Promise<Message[]> {
  //   try {
  //     const response = await api.get<Message[]>(`/chat/${sessionId}/messages`);
  
  //     // Filter out Ask-on-DF messages
  //     const filteredMessages = response.data.filter((message) => !message.df_parent);
  
  //     return filteredMessages;
  //   } catch (error: any) {
  //     throw new Error(error.response?.data?.detail || 'Failed to fetch session messages');
  //   }
  // }

  static async getSessionMessages(sessionId: string): Promise<Message[]> {
    try {
      const response = await api.get<Message[]>(`/chat/${sessionId}/messages`);
      
      // Filter out Ask-on-DF messages
      const filteredMessages = response.data.filter(message => !message.df_parent);
      
      return filteredMessages;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch session messages');
    }
  }
  

  static async deleteChatSession(sessionId: string): Promise<void> {
    try {
      await api.delete(`/chat/sessions/${sessionId}`);
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to delete chat session');
    }
  }



  static async askOnDF(
    sessionId: string, 
    messageId: string, 
    question: string
  ): Promise<Message> {
    const response = await api.post<Message>(
      `/chat/${sessionId}/ask_on_df/${messageId}`, // messageId identifies the parent DF
      { question } // Only send the question
    );
    return response.data;
  }
  
  

  

}