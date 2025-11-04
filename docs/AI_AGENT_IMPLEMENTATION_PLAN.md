# 🤖 AI Agent Implementation Plan - Waymo Dashboard

**Goal:** Add Gemini AI agent with SQL query capabilities to enable natural language data exploration  
**Timeline:** Single day implementation (8-10 hours)  
**Date Created:** November 2, 2025

---

## 📋 Overview

### What We're Building
A sidebar chat interface powered by Google's Gemini AI agent that can:
- Answer natural language questions about edge case data
- Autonomously write and execute SQL queries
- Provide data insights with specific numbers
- Self-correct when queries fail

### Architecture Choice
**Text-to-SQL Approach** - Single powerful `execute_sql_query` tool with full database schema
- Agent generates SQL queries based on user questions
- More flexible than predefined query tools
- Simpler to maintain and extend

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                   │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Chat Sidebar    │         │   Dashboard       │         │
│  │  - Input box     │         │   - Charts        │         │
│  │  - Messages      │◄────────┤   - Filters       │         │
│  │  - SQL display   │         │   - Tables        │         │
│  └────────┬─────────┘         └───────────────────┘         │
│           │ POST /api/agent/chat                             │
└───────────┼──────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (main.py)                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Gemini Agent Orchestrator                │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  Model: gemini-1.5-pro                         │  │  │
│  │  │  System: Data analyst with DB schema          │  │  │
│  │  │  Tool: execute_sql_query()                     │  │  │
│  │  └──────────────────┬─────────────────────────────┘  │  │
│  │                     │                                  │  │
│  │                     ▼                                  │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │       SQL Query Executor + Safety Layer        │  │  │
│  │  │  - Validate: Only SELECT                       │  │  │
│  │  │  - Enforce: LIMIT, read-only connection        │  │  │
│  │  │  - Sanitize: No injection, comments, etc.      │  │  │
│  │  └──────────────────┬─────────────────────────────┘  │  │
│  └────────────────────┼────────────────────────────────┘  │
│                       │                                    │
└───────────────────────┼────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│          SQLite Database (edge_cases.db) - READ ONLY        │
│  ┌────────────────┐              ┌──────────────────┐      │
│  │  frames table  │              │ edge_cases table │      │
│  │  - motion data │              │ - severity       │      │
│  └────────────────┘              └──────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Implementation Checklist

### Phase 1: Backend Foundation (2-3 hours)

#### 1.1 Environment Setup
- [ ] Install Google Generative AI SDK
  ```bash
  cd waymo-api
  pip install google-generativeai
  ```
- [ ] Add to `requirements.txt`:
  ```
  google-generativeai>=0.3.0
  ```
- [ ] Add `GEMINI_API_KEY` to `.env` file
- [ ] Test API key with simple ping

#### 1.2 SQL Safety Module (`sql_validator.py`)
- [ ] Create `waymo-api/sql_validator.py`
- [ ] Implement `is_safe_query()` function
  - Only SELECT allowed
  - Blacklist: INSERT, UPDATE, DELETE, DROP, etc.
  - No SQL comments (`--`, `/**/`)
  - No multiple statements (`;` check)
- [ ] Implement `execute_sql_query()` function
  - Read-only SQLite connection
  - Enforce LIMIT (max 1000 rows)
  - Return structured response with success/error
- [ ] Write 5-10 unit tests for edge cases

#### 1.3 Agent Tool Definition (`agent_tools.py`)
- [ ] Create `waymo-api/agent_tools.py`
- [ ] Define `execute_sql_query` tool with:
  - Full database schema in description
  - Query examples for common patterns
  - Parameter definitions (query, limit)
- [ ] Define system prompt with:
  - Role: Data analyst for Waymo edge cases
  - Guidelines: Always use tool, explain findings
  - Response style: Concise with numbers

#### 1.4 Agent Endpoint (`main.py`)
- [ ] Create `/api/agent/chat` POST endpoint
- [ ] Initialize Gemini agent with tool
- [ ] Implement tool call loop:
  - Send user message
  - Handle `execute_sql_query` calls
  - Return results to agent
  - Get final text response
- [ ] Add error handling and logging
- [ ] Add rate limiting (20 queries/minute)

**Expected Output:**
```bash
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many high severity cases are there?"}'

# Response:
{
  "response": "Found 234 high severity cases (severity > 0.8)...",
  "tool_calls": [{
    "query": "SELECT COUNT(*) FROM edge_cases WHERE severity > 0.8",
    "row_count": 1
  }]
}
```

---

### Phase 2: Frontend Chat UI (3-4 hours)

#### 2.1 Chat Hook (`useAgentChat.ts`)
- [ ] Create `Waymo-Dash/src/hooks/useAgentChat.ts`
- [ ] Implement state management:
  ```typescript
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  ```
- [ ] Implement `sendMessage()` function:
  - Add user message to state
  - Call `/api/agent/chat`
  - Add agent response to state
- [ ] Handle conversation history
- [ ] Handle errors gracefully

#### 2.2 Chat Sidebar Component (`ChatSidebar.tsx`)
- [ ] Create `Waymo-Dash/src/components/dashboard/ChatSidebar.tsx`
- [ ] Build UI structure:
  - Header with title and collapse button
  - Scrollable message area
  - Input box with send button
  - Suggested questions (chips)
- [ ] Style with Tailwind + CSS variables
- [ ] Add auto-scroll to latest message
- [ ] Add typing indicator while loading

#### 2.3 Message Component (`ChatMessage.tsx`)
- [ ] Create `Waymo-Dash/src/components/dashboard/ChatMessage.tsx`
- [ ] Display user messages (right-aligned)
- [ ] Display agent messages (left-aligned)
- [ ] Show SQL queries in collapsible `<details>`:
  ```tsx
  <details>
    <summary>🔍 SQL Query (234 rows)</summary>
    <pre className="sql-code">{query}</pre>
  </details>
  ```
- [ ] Add copy-to-clipboard button for responses
- [ ] Add markdown rendering for agent responses

#### 2.4 Integration with Dashboard (`Index.tsx`)
- [ ] Add `ChatSidebar` component to layout
- [ ] Make it collapsible (localStorage persistence)
- [ ] Position: Right sidebar (300-400px wide)
- [ ] Add keyboard shortcut to toggle (Cmd/Ctrl + K)

#### 2.5 Suggested Questions
- [ ] Create `suggestedQuestions.ts` with context-aware logic:
  ```typescript
  const getSuggestions = (dashboardState) => {
    const base = [
      "How many edge cases are there?",
      "Show me the most dangerous scenarios",
      "What's the average speed during high severity events?"
    ]
    
    if (dashboardState.highSeverityCount > 100) {
      base.push("Why are there so many high severity cases?")
    }
    
    return base
  }
  ```
- [ ] Display as clickable chips above input box
- [ ] Auto-fill input when clicked

**Expected Output:**
- Clean chat interface with message bubbles
- Shows SQL queries used by agent
- Responsive and accessible
- Works on mobile

---

### Phase 3: Polish & Testing (2-3 hours)

#### 3.1 Security Hardening
- [ ] Test SQL injection attempts:
  - `'; DROP TABLE frames; --`
  - `UNION SELECT * FROM sqlite_master`
  - Multiple statements
- [ ] Verify read-only connection works
- [ ] Test rate limiting (spam 30+ requests)
- [ ] Add query timeout (5 seconds)
- [ ] Add audit logging for all queries

#### 3.2 Error Handling
- [ ] Test with invalid SQL syntax
- [ ] Test with non-existent columns
- [ ] Test with Gemini API down (mock)
- [ ] Test with database locked
- [ ] Add user-friendly error messages:
  - "Sorry, I couldn't execute that query"
  - "The database is busy, try again"
  - "I'm having trouble connecting, please wait"

#### 3.3 Performance Optimization
- [ ] Cache common queries (LRU cache, 100 entries)
- [ ] Add loading states for slow queries
- [ ] Optimize SQL queries (add indexes if needed)
- [ ] Test with 10+ concurrent users

#### 3.4 User Testing
- [ ] Test 20+ real user questions:
  - "Show me high severity cases"
  - "What's the average speed during right turns?"
  - "Find frames with unusual jerk patterns"
  - "Compare left vs right turn safety"
  - "Which files have the most edge cases?"
- [ ] Verify agent generates correct SQL
- [ ] Verify agent handles ambiguous questions
- [ ] Verify agent self-corrects on errors

#### 3.5 Documentation
- [ ] Add usage examples to README
- [ ] Document available query patterns
- [ ] Add troubleshooting guide
- [ ] Document rate limits and quotas

---

## 📝 Code Templates

### Backend: `sql_validator.py`

```python
import sqlite3
import re
from typing import Any, Dict, Tuple

DB_PATH = "./waymo_dataset/results/edge_cases.db"

def is_safe_query(query: str) -> Tuple[bool, str]:
    """
    Validate SQL query for safety.
    
    Returns:
        (is_safe: bool, message: str)
    """
    query_upper = query.upper().strip()
    
    # Only SELECT allowed
    if not query_upper.startswith("SELECT"):
        return False, "Only SELECT queries are allowed"
    
    # Forbidden keywords
    forbidden = [
        "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", 
        "ALTER", "TRUNCATE", "REPLACE", "PRAGMA",
        "ATTACH", "DETACH", "VACUUM"
    ]
    
    for keyword in forbidden:
        if re.search(rf'\b{keyword}\b', query_upper):
            return False, f"Keyword '{keyword}' is not allowed"
    
    # No SQL comments
    if "--" in query or "/*" in query:
        return False, "SQL comments are not allowed"
    
    # No multiple statements
    if ";" in query[:-1]:
        return False, "Multiple statements are not allowed"
    
    return True, "OK"


def execute_sql_query(query: str, limit: int = 100) -> Dict[str, Any]:
    """
    Execute SQL query with safety checks.
    
    Args:
        query: SQL SELECT statement
        limit: Max rows to return (default 100, max 1000)
    
    Returns:
        {
            "success": bool,
            "data": list[dict] | None,
            "error": str | None,
            "row_count": int,
            "query_executed": str
        }
    """
    limit = min(limit, 1000)
    
    # Validate safety
    is_safe, message = is_safe_query(query)
    if not is_safe:
        return {
            "success": False,
            "data": None,
            "error": f"Unsafe query: {message}",
            "row_count": 0,
            "query_executed": query
        }
    
    # Enforce LIMIT
    if "LIMIT" not in query.upper():
        query = f"{query.rstrip(';')} LIMIT {limit}"
    
    try:
        # Read-only connection
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        data = [dict(row) for row in rows]
        conn.close()
        
        return {
            "success": True,
            "data": data,
            "error": None,
            "row_count": len(data),
            "query_executed": query
        }
        
    except sqlite3.Error as e:
        return {
            "success": False,
            "data": None,
            "error": f"SQL Error: {str(e)}",
            "row_count": 0,
            "query_executed": query
        }
```

---

### Backend: `agent_tools.py`

```python
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

# Database schema for agent
DB_SCHEMA = """
TABLE: frames
- frame_id (INTEGER PRIMARY KEY) - Unique frame identifier
- file_name (TEXT) - Source tfrecord file
- intent (TEXT) - GO_STRAIGHT, GO_LEFT, GO_RIGHT, STOP
- speed_max (REAL) - Max speed (m/s)
- speed_min (REAL) - Min speed (m/s)
- accel_x_min (REAL) - Min longitudinal accel (m/s²), negative = braking
- accel_x_max (REAL) - Max longitudinal accel
- accel_y_min (REAL) - Min lateral accel
- accel_y_max (REAL) - Max lateral accel
- jerk_x_min (REAL) - Min longitudinal jerk (m/s³)
- jerk_x_max (REAL) - Max longitudinal jerk
- jerk_y_min (REAL) - Min lateral jerk
- jerk_y_max (REAL) - Max lateral jerk
- panorama_thumbnail (BLOB) - Base64 image

TABLE: edge_cases
- id (INTEGER PRIMARY KEY)
- frame_id (INTEGER) - References frames(frame_id)
- edge_case_type (TEXT) - Edge case category
- severity (REAL) - Score 0-1
- description (TEXT) - Human-readable description

COMMON PATTERNS:
- Join tables: SELECT f.*, ec.severity FROM frames f 
               LEFT JOIN edge_cases ec ON f.frame_id = ec.frame_id
- Filter by severity: WHERE ec.severity > 0.8
- Group by intent: GROUP BY f.intent
"""

# Tool definition
sql_query_tool = Tool(
    function_declarations=[
        FunctionDeclaration(
            name="execute_sql_query",
            description=f"""
Execute a SQL query on the Waymo edge case database.

{DB_SCHEMA}

QUERY RULES:
1. Always use LIMIT (default 100, max 1000)
2. Use meaningful aliases for aggregations
3. Handle NULLs with COALESCE()
4. Round floats to 2-3 decimals
5. Exclude panorama_thumbnail unless specifically needed

EXAMPLES:
Q: "High severity right turns"
A: SELECT f.*, ec.severity 
   FROM frames f 
   JOIN edge_cases ec ON f.frame_id = ec.frame_id 
   WHERE f.intent = 'GO_RIGHT' AND ec.severity > 0.8 
   LIMIT 50

Q: "Average speed by intent"
A: SELECT intent, ROUND(AVG(speed_max), 2) as avg_speed, COUNT(*) as count
   FROM frames 
   GROUP BY intent 
   ORDER BY avg_speed DESC
            """,
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Valid SQL SELECT statement"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max rows (default 100, max 1000)",
                        "default": 100
                    }
                },
                "required": ["query"]
            }
        )
    ]
)

# System instruction
SYSTEM_INSTRUCTION = """
You are an expert data analyst for Waymo autonomous vehicle edge case detection.

Your job is to help users understand edge case patterns by writing SQL queries.

GUIDELINES:
1. ALWAYS use execute_sql_query tool - never assume data
2. Write efficient SQL with appropriate JOINs
3. Use LIMIT to keep results manageable
4. Explain findings with specific numbers
5. If a query fails, try a simpler approach
6. Suggest follow-up questions for interesting patterns

RESPONSE STYLE:
- Start with key insight ("Found 234 cases...")
- Include specific numbers and percentages
- Keep concise (2-4 sentences)
- Suggest visualizations when relevant

EXAMPLE:
User: "Why so many severe right turns?"
You: [Execute query to check GO_RIGHT severity]
You: "Found 89 high-severity right turns (avg severity 0.84). 
      78% occur at speeds >15 m/s with lateral accel >0.6 m/s². 
      This suggests aggressive lane changes during turns."
"""

def get_agent_model():
    """Initialize Gemini agent with SQL tool"""
    return genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        tools=[sql_query_tool],
        system_instruction=SYSTEM_INSTRUCTION
    )
```

---

### Backend: `/api/agent/chat` Endpoint

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from sql_validator import execute_sql_query
from agent_tools import get_agent_model

app = FastAPI()

# Configure API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    conversation_history: list = []

@app.post("/api/agent/chat")
async def chat_with_agent(request: ChatRequest):
    """
    Chat with AI agent that can query database
    """
    try:
        agent = get_agent_model()
        chat = agent.start_chat(history=request.conversation_history)
        
        # Send user message
        response = chat.send_message(request.message)
        
        # Handle tool calls
        tool_calls = []
        max_iterations = 5  # Prevent infinite loops
        iterations = 0
        
        while iterations < max_iterations:
            if not response.candidates:
                break
                
            part = response.candidates[0].content.parts[0]
            
            if hasattr(part, 'function_call'):
                function_call = part.function_call
                
                if function_call.name == "execute_sql_query":
                    # Execute SQL
                    result = execute_sql_query(
                        query=function_call.args.get("query"),
                        limit=function_call.args.get("limit", 100)
                    )
                    
                    # Track for transparency
                    tool_calls.append({
                        "tool": "execute_sql_query",
                        "query": result["query_executed"],
                        "row_count": result["row_count"],
                        "success": result["success"],
                        "error": result.get("error")
                    })
                    
                    # Send result back to agent
                    response = chat.send_message(
                        genai.protos.Content(parts=[
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name="execute_sql_query",
                                    response={"result": result}
                                )
                            )
                        ])
                    )
                    iterations += 1
                else:
                    break
            else:
                break
        
        return {
            "response": response.text,
            "tool_calls": tool_calls,
            "conversation_history": chat.history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### Frontend: `useAgentChat.ts`

```typescript
import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';

const API_BASE = "http://localhost:8000";

interface Message {
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: Array<{
    tool: string;
    query: string;
    row_count: number;
    success: boolean;
  }>;
}

export const useAgentChat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationHistory, setConversationHistory] = useState([]);

  const sendMessageMutation = useMutation({
    mutationFn: async (message: string) => {
      const response = await fetch(`${API_BASE}/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          conversation_history: conversationHistory
        })
      });
      
      if (!response.ok) throw new Error('Failed to send message');
      return response.json();
    },
    onMutate: (message) => {
      // Optimistically add user message
      setMessages(prev => [...prev, { role: 'user', content: message }]);
    },
    onSuccess: (data) => {
      // Add agent response
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        toolCalls: data.tool_calls
      }]);
      
      // Update conversation history
      setConversationHistory(data.conversation_history);
    },
    onError: (error) => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error.message}`
      }]);
    }
  });

  const sendMessage = (message: string) => {
    sendMessageMutation.mutate(message);
  };

  const clearChat = () => {
    setMessages([]);
    setConversationHistory([]);
  };

  return {
    messages,
    sendMessage,
    clearChat,
    isLoading: sendMessageMutation.isPending
  };
};
```

---

### Frontend: `ChatSidebar.tsx`

```typescript
import { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAgentChat } from '@/hooks/useAgentChat';
import { Send, Sparkles, X } from 'lucide-react';

const SUGGESTED_QUESTIONS = [
  "How many high severity cases are there?",
  "Show me the most dangerous scenarios",
  "What's the average speed during right turns?",
  "Find frames with unusual jerk patterns"
];

export const ChatSidebar = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { messages, sendMessage, isLoading, clearChat } = useAgentChat();

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput('');
  };

  const handleSuggestionClick = (question: string) => {
    setInput(question);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-card border-l border-border shadow-elevated z-50">
      <Card className="h-full flex flex-col">
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            AI Data Analyst
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>

        <CardContent className="flex-1 flex flex-col gap-4 overflow-hidden">
          {/* Suggested Questions */}
          {messages.length === 0 && (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Try asking:</p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTED_QUESTIONS.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSuggestionClick(q)}
                    className="text-xs px-3 py-1.5 rounded-full bg-primary/10 hover:bg-primary/20 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-4">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-lg p-3 ${
                  msg.role === 'user' 
                    ? 'bg-primary text-primary-foreground' 
                    : 'bg-muted'
                }`}>
                  <p className="text-sm">{msg.content}</p>
                  
                  {/* Show SQL queries */}
                  {msg.toolCalls?.map((call, i) => (
                    <details key={i} className="mt-2 text-xs">
                      <summary className="cursor-pointer opacity-70">
                        🔍 SQL Query ({call.row_count} rows)
                      </summary>
                      <pre className="mt-1 p-2 bg-background/50 rounded overflow-x-auto">
                        {call.query}
                      </pre>
                    </details>
                  ))}
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-lg p-3">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-foreground/50 rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-foreground/50 rounded-full animate-bounce delay-100" />
                    <div className="w-2 h-2 bg-foreground/50 rounded-full animate-bounce delay-200" />
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about the data..."
              className="flex-1 px-3 py-2 rounded-lg border border-border bg-background"
              disabled={isLoading}
            />
            <Button onClick={handleSend} disabled={isLoading || !input.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
```

---

## ⚠️ Known Limitations & Future Improvements

### Current Limitations
1. **No chart generation** - Agent can only return text/data
2. **No dashboard control** - Can't apply filters or trigger UI changes
3. **No image analysis** - Can't view/analyze thumbnails
4. **Query timeout** - Complex queries might exceed 5s limit
5. **Cost** - Gemini API calls cost money (monitor usage)

### Future Enhancements (v2)
- [ ] Add `apply_dashboard_filter()` tool to control UI
- [ ] Add `get_frame_thumbnail()` tool for image retrieval
- [ ] Add chart generation (return Vega-Lite specs)
- [ ] Add query caching with Redis
- [ ] Add user feedback (👍👎) to improve prompts
- [ ] Add export chat to PDF/Markdown
- [ ] Add voice input (speech-to-text)
- [ ] Add streaming responses for faster UX

---

## 🔐 Security Checklist

- [ ] ✅ Read-only database connection
- [ ] ✅ SQL query validation (whitelist SELECT)
- [ ] ✅ No SQL injection (sanitize all inputs)
- [ ] ✅ Rate limiting (20 queries/minute)
- [ ] ✅ Query timeout (5 seconds)
- [ ] ✅ Row limit enforcement (max 1000)
- [ ] ✅ API key in environment variable (not committed)
- [ ] ✅ Audit logging for all queries
- [ ] ✅ Error messages don't leak sensitive info

---

## 📊 Success Metrics

### Must Have (MVP)
- [ ] Agent can answer 90%+ of test questions correctly
- [ ] SQL queries are syntactically correct
- [ ] Response time < 5 seconds for simple queries
- [ ] No security vulnerabilities in testing
- [ ] Zero data modification attempts succeed

### Nice to Have
- [ ] Agent self-corrects on 80%+ of failed queries
- [ ] Users prefer chat over manual SQL
- [ ] Average conversation length > 3 messages
- [ ] Chat used in 50%+ of dashboard sessions

---

## 🚀 Launch Day Timeline

### Morning (4 hours)
- **08:00-09:00** - Backend setup + SQL validator
- **09:00-10:30** - Agent tool definition + system prompt
- **10:30-12:00** - `/api/agent/chat` endpoint + testing

### Afternoon (4 hours)
- **13:00-14:30** - Frontend chat hook + UI components
- **14:30-15:30** - Integration with dashboard
- **15:30-16:30** - Testing with real questions

### Evening (2 hours)
- **17:00-18:00** - Bug fixes + polish
- **18:00-19:00** - Security testing + documentation

---

## 📚 References

- [Google Gemini API Docs](https://ai.google.dev/docs)
- [Function Calling Guide](https://ai.google.dev/docs/function_calling)
- [SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [React Query Docs](https://tanstack.com/query/latest)

---

## 💡 Tips for Success

1. **Test early, test often** - Don't wait until the end to test queries
2. **Start with simple questions** - "How many rows?" before complex analytics
3. **Log everything** - You'll need it for debugging
4. **Use the playground** - Test Gemini prompts in AI Studio first
5. **Read error messages** - Agent's SQL errors are goldmines for improvement
6. **Keep schema updated** - If DB changes, update tool description
7. **Monitor costs** - Set up billing alerts in Google Cloud
8. **Have fun!** - This is the cool part! 🎉

---

**Next Steps:** Start with Phase 1.1 (Environment Setup) and work through checklist sequentially. Good luck! 🚀
