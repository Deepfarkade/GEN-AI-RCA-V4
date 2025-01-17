import React, { useState, useEffect } from "react";
import { Mic, Send, Bot, Plus, MessageSquare, LogOut, ChevronLeft, ChevronRight, Download, Home, Sun, Moon, ArrowRight, User } from 'lucide-react';
import { Message } from "../features/chat/types";
import { ChatService } from "../features/chat/services/chatService";

interface AsddfProps {
  open: boolean;
  onClose: () => void;
  sessionId: string;
  parentMessageId?: string;
  tableData: {
    columns: string[];
    records: Array<Record<string, any>>;
  };
  summary?: string;
  existingDFMessages?: Message[];
}

export default function Asddf({
  open,
  onClose,
  sessionId,
  parentMessageId,
  tableData,
  summary,
  existingDFMessages = [],
}: AsddfProps) {
  const [dfQuestions, setDfQuestions] = useState<Message[]>([]);
  const [inputQuery, setInputQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Load existing DF messages when the popup opens
  useEffect(() => {
    const fetchChatHistory = async () => {
      if (open) {
        try {
          const messages = await ChatService.getSessionMessages(sessionId);
          const dfMessages = messages.filter(
            (msg) => msg.df_parent === parentMessageId
          );
          setDfQuestions(dfMessages);
        } catch (error) {
          console.error("Failed to fetch chat history:", error);
        }
      }
    };

    fetchChatHistory();
  }, [open, sessionId, parentMessageId]);

  const handleAskOnDF = async () => {
    if (!inputQuery.trim()) return;
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: "user",
      role: "user",
      text: inputQuery,
      timestamp: new Date(),
      sessionId,
    };
    setDfQuestions((prev) => [...prev, userMsg]);

    try {
      const response: Message = await ChatService.askOnDF(
        sessionId,
        parentMessageId || "",
        inputQuery
      );
      setDfQuestions((prev) => [...prev, response]);
    } catch (error) {
      console.error("Failed to ask on DF:", error);
      setDfQuestions((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          sender: "bot",
          role: "assistant",
          text: "An error occurred while asking on DF. Please try again.",
          timestamp: new Date(),
          sessionId,
        },
      ]);
    } finally {
      setIsLoading(false);
      setInputQuery("");
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="relative w-[91%] h-[91%] bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg overflow-hidden">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 bg-red-500 text-white px-2 py-1 rounded hover:bg-red-600 z-50"
          style={{ zIndex: 50 }} // Ensure it's above other elements
        >
          X
        </button>

        {/* Table Section */}
        <div className="h-[40%] overflow-y-auto mb-4">
          <table className="table-auto border-collapse border border-gray-300 w-full text-xs">
            <thead className="bg-yellow-500 text-black sticky top-0">
              <tr>
                {tableData.columns.map((col, idx) => (
                  <th key={idx} className="border border-gray-300 px-4 py-2">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-gray-700 text-gray-200">
              {tableData.records.map((record, rowIndex) => (
                <tr key={rowIndex} className="hover:bg-gray-600">
                  {tableData.columns.map((col, colIndex) => (
                    <td
                      key={colIndex}
                      className={`border border-gray-500 px-4 py-2 ${
                        typeof record[col] === "number" ? "text-right" : "text-left"
                      }`}
                    >
                      {record[col]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Chat Section */}

        {/* Chat Section */}
        <div className="h-[59.5%] flex flex-col border-t border-gray-500 p-4 bg-gray-50 dark:bg-gray-700 rounded">
          {/* Chat History */}
          {/* Chat History */}
          <div className="flex-1 overflow-y-auto mb-4 px-6 py-4" style={{ maxHeight: "100%", fontSize: "0.700rem" }}>
            {dfQuestions.length === 0 ? (
              <p className="text-gray-400 text-sm">
                No conversation yet. Ask your first question about this DF!
              </p>
            ) : (
              dfQuestions.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex items-start p-4 mb-3 rounded-lg max-w-[80%] ${
                    msg.sender === "user"
                      ? "bg-yellow-500 text-black self-end shadow-xl"
                      : "bg-gray-300 text-black self-start shadow-md"
                  }`}
                >
                  {/* Icon */}
                  <div className="flex-shrink-0 mr-3">
                    {msg.sender === "user" ? (
                      <div className="w-6 h-6 text-yellow-700">
                        <User /> {/* Replace with your desired user icon */}
                      </div>
                    ) : (
                      <div className="w-6 h-6 text-gray-700">
                        <Bot /> {/* Bot icon */}
                      </div>
                    )}
                  </div>

                  {/* Message Content */}
                  {/* Message Content */}
                  <div>
                    {msg.sender === "bot" ? (
                      <div className="whitespace-pre-wrap">
                        {/* Render Markdown-like format */}
                        {msg.text.split("\n").map((line, index) => {
                          if (line.startsWith("###")) {
                            // Headings
                            return (
                              <h3 key={index} className="text-xl font-bold mt-3 text-blue-600">
                                {line.replace("###", "").trim()}
                              </h3>
                            );
                          } else if (line.includes("**")) {
                            // Bold Text
                            return (
                              <p
                                key={index}
                                className="font-semibold"
                                dangerouslySetInnerHTML={{
                                  __html: line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>"),
                                }}
                              />
                            );
                          } else if (line.startsWith("1.") || line.startsWith("2.")) {
                            // Ordered Lists
                            return (
                              <ul key={index} className="list-decimal pl-6">
                                <li>{line}</li>
                              </ul>
                            );
                          } else {
                            // Regular Paragraph
                            return <p key={index}>{line}</p>;
                          }
                        })}
                      </div>
                    ) : (
                      // For User Messages
                      <p>{msg.text}</p>
                    )}
                  </div>

                </div>
              ))
            )}

            {/* Loader or Animation During Response */}
            {isLoading && (
              <div className="flex items-center justify-start p-4 mb-3 max-w-[80%] bg-gray-300 text-black self-start rounded-lg shadow-md">
                <div className="w-6 h-6 mr-3 animate-spin border-4 border-gray-500 border-t-transparent rounded-full"></div>
                <p>Agent is thinking...</p>
              </div>
            )}
          </div>


          {/* Input Section */}
          <div className="flex items-center space-x-4 mt-4 px-6">
            <input
              type="text"
              className="flex-1 px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-400 transition-all shadow-lg"
              placeholder="Ask something about this DF..."
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !isLoading) {
                  setInputQuery(""); // Clear input immediately
                  handleAskOnDF();
                }
              }}
              disabled={isLoading} // Disable input when loading
              style={{ maxHeight: "80px", fontSize: "0.875rem" }} // Slightly smaller font size and proportional height
            />
            <button
              onClick={() => {
                setInputQuery(""); // Clear input immediately
                handleAskOnDF();
              }}
              disabled={isLoading}
              className="bg-yellow-500 text-black px-6 py-3 rounded-lg hover:bg-yellow-600 transition-all disabled:opacity-50"
            >
              {isLoading ? "Thinking..." : "Send"}
            </button>
          </div>
        </div>


      </div>
    </div>
  );
}
