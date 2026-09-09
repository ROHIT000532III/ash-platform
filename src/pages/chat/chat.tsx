import { useEffect, useMemo, useRef, useState } from "react";
import MarkdownContent from "../../components/MarkdownContent";
import { createConversation, deleteConversation, getChatSettings, getConversation, getConversations, renameConversation, sendChat, streamChat } from "../../services/api";
import type { ChatMessage, Conversation } from "../../services/api";

type Attempt = { message: string; conversationId: string; regenerate: boolean };
const errorText = (error: unknown) => error instanceof Error ? error.message : "Unable to reach ASH AI.";

export default function Chat() {
  const [draft, setDraft] = useState(""); const [messages, setMessages] = useState<ChatMessage[]>([]); const [conversations, setConversations] = useState<Conversation[]>([]); const [activeId, setActiveId] = useState<string | null>(null); const [search, setSearch] = useState(""); const [loading, setLoading] = useState(false); const [error, setError] = useState(""); const [lastAttempt, setLastAttempt] = useState<Attempt | null>(null);
  const controller = useRef<AbortController | null>(null); const messagesRef = useRef<HTMLDivElement>(null); const shouldScroll = useRef(true);
  const load = async () => { try { setConversations(await getConversations()); } catch (e) { setError(errorText(e)); } };
  useEffect(() => {
    void getConversations().then(setConversations).catch((e) => setError(errorText(e)));
  }, []);
  useEffect(() => { if (shouldScroll.current) messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: "smooth" }); }, [messages, loading]);
  const visible = useMemo(() => conversations.filter((c) => c.title.toLowerCase().includes(search.trim().toLowerCase())), [conversations, search]);
  const newChat = () => { if (!loading) { setActiveId(null); setMessages([]); setDraft(""); setError(""); setLastAttempt(null); } };
  const select = async (id: string) => { if (loading) return; try { const item = await getConversation(id); setActiveId(id); setMessages(item.messages.map(({ role, content }) => ({ role, content }))); setError(""); } catch (e) { setError(errorText(e)); } };
  const remove = async (id: string, title: string) => { if (loading || !window.confirm(`Delete "${title}" and all messages?`)) return; try { await deleteConversation(id); if (activeId === id) newChat(); await load(); } catch (e) { setError(errorText(e)); } };
  const rename = async (id: string, title: string) => { const next = window.prompt("Conversation title", title)?.trim(); if (!next) return; try { await renameConversation(id, next); await load(); } catch (e) { setError(errorText(e)); } };
  const run = async (attempt: Attempt) => {
    if (loading) return; shouldScroll.current = true; setLoading(true); setError(""); setLastAttempt(attempt);
    if (attempt.regenerate) setMessages((items) => items.at(-1)?.role === "assistant" ? [...items.slice(0, -1), { role: "assistant", content: "" }] : [...items, { role: "assistant", content: "" }]);
    else setMessages((items) => [...items, { role: "user", content: attempt.message }, { role: "assistant", content: "" }]);
    try {
      let response = ""; controller.current = new AbortController(); const append = (delta: string) => { response += delta; setMessages((items) => [...items.slice(0, -1), { role: "assistant", content: response }]); };
      const settings = getChatSettings();
      if (settings.streaming) await streamChat(attempt.message, messages, append, attempt.conversationId, settings, attempt.regenerate, controller.current.signal);
      else append(await sendChat(attempt.message, messages, attempt.conversationId, settings, attempt.regenerate));
      await load();
    } catch (e) {
      const stopped = e instanceof DOMException && e.name === "AbortError";
      setError(stopped ? "Generation stopped. Received text is kept locally; retry will not duplicate your message." : errorText(e));
      setLastAttempt({ ...attempt, regenerate: true });
      setMessages((items) => items.at(-1)?.role === "assistant" && !items.at(-1)?.content ? items.slice(0, -1) : items);
    } finally { controller.current = null; setLoading(false); }
  };
  const submit = async () => { const text = draft.trim(); if (!text || loading) return; let id = activeId; if (!id) { try { id = (await createConversation()).id; setActiveId(id); } catch (e) { setError(errorText(e)); return; } } setDraft(""); await run({ message: text, conversationId: id, regenerate: false }); };
  const regenerate = () => { if (!activeId || messages.at(-1)?.role !== "assistant") return; const user = [...messages].reverse().find((item) => item.role === "user"); if (user) void run({ message: user.content, conversationId: activeId, regenerate: true }); };
  return <div className="ash-chat-layout"><aside className="conversation-sidebar"><button className="new-chat-button" type="button" onClick={newChat}>+ New Chat</button><input className="conversation-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search chats" />{!visible.length && <p className="conversation-empty">No matching conversations.</p>}<div className="conversation-list">{visible.map((c) => <div className={`conversation-item ${activeId === c.id ? "active" : ""}`} key={c.id}><button type="button" onClick={() => void select(c.id)}>{c.title}</button><button type="button" aria-label={`Rename ${c.title}`} onClick={() => void rename(c.id, c.title)}>Rename</button><button className="delete-conversation" type="button" aria-label={`Delete ${c.title}`} onClick={() => void remove(c.id, c.title)}>Delete</button></div>)}</div></aside><main className="ash-chat"><header className="ash-chat-header"><div><h1>ASH AI</h1><p>Enterprise AI Assistant</p></div><div className="chat-account"><span>Local Workspace</span><div className="status"><span className="status-dot" />{loading ? "THINKING" : "ONLINE"}</div></div></header>{error && <div className="chat-error">{error} {!loading && lastAttempt && <button type="button" onClick={() => void run(lastAttempt)}>Retry</button>}</div>}<div className="ash-chat-messages" ref={messagesRef} onScroll={(e) => { const el = e.currentTarget; shouldScroll.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80; }} aria-live="polite">{messages.length === 0 && <div className="empty-chat"><h2>Welcome to ASH AI</h2><p>Start a new chat or select a saved conversation.</p></div>}{messages.map((item, index) => <div key={`${item.role}-${index}`} className={`message ${item.role}-message`}><div className="message-role">{item.role === "user" ? "YOU" : "ASH AI"}</div><div className="message-content">{item.content ? item.role === "assistant" ? <MarkdownContent content={item.content} /> : item.content : "Thinking..."}</div>{item.role === "assistant" && item.content && <div className="message-actions"><button type="button" onClick={() => void navigator.clipboard?.writeText(item.content)}>Copy Response</button>{index === messages.length - 1 && <button type="button" disabled={loading} onClick={regenerate}>Regenerate</button>}</div>}</div>)}</div><div className="ash-chat-input"><textarea value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void submit(); } }} placeholder="Message ASH AI..." disabled={loading}/>{loading ? <button type="button" onClick={() => controller.current?.abort()}>Stop</button> : <button type="button" disabled={!draft.trim()} onClick={() => void submit()}>Send</button>}</div></main></div>;
}
