import { useMutation } from "@tanstack/react-query";

interface ChatRequest {
  message: string;
}

interface ChatResponse {
  response: string;
}

const sendChatMessage = async (message: string): Promise<ChatResponse> => {
  const response = await fetch("http://localhost:8000/api/agent/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    throw new Error("Failed to send message");
  }

  return response.json();
};

export const useAgentChat = () => {
  return useMutation({
    mutationFn: sendChatMessage,
    onSuccess: (data) => {
      console.log("Message sent successfully:", data);
    },
    onError: (error) => {
      console.error("Error sending message:", error);
    },
  });
};
