import type { ReactNode } from "react";

function copyCode(text: string) { void navigator.clipboard?.writeText(text); }
function inline(text: string): ReactNode[] {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^\s)]+\))/g).map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) return <code key={index}>{part.slice(1, -1)}</code>;
    if (part.startsWith("**")) return <strong key={index}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("*")) return <em key={index}>{part.slice(1, -1)}</em>;
    const link = part.match(/^\[([^\]]+)\]\(([^\s)]+)\)$/);
    return link ? <a key={index} href={link[2]} target="_blank" rel="noreferrer noopener">{link[1]}</a> : part;
  });
}

function textBlock(text: string, key: string) {
  const lines = text.split("\n"); const nodes: ReactNode[] = []; let list: ReactNode[] = [];
  const flush = () => { if (list.length) { nodes.push(<ul key={`${key}-list-${nodes.length}`}>{list}</ul>); list = []; } };
  lines.forEach((line, i) => {
    const listItem = line.match(/^[-*+]\s+(.+)/) || line.match(/^\d+\.\s+(.+)/);
    if (listItem) { list.push(<li key={`${key}-${i}`}>{inline(listItem[1])}</li>); return; }
    flush(); if (!line) { nodes.push(<br key={`${key}-${i}`} />); return; }
    if (line.startsWith("> ")) nodes.push(<blockquote key={`${key}-${i}`}>{inline(line.slice(2))}</blockquote>);
    else if (line.startsWith("### ")) nodes.push(<h3 key={`${key}-${i}`}>{inline(line.slice(4))}</h3>);
    else if (line.startsWith("## ")) nodes.push(<h2 key={`${key}-${i}`}>{inline(line.slice(3))}</h2>);
    else if (line.startsWith("# ")) nodes.push(<h1 key={`${key}-${i}`}>{inline(line.slice(2))}</h1>);
    else nodes.push(<p key={`${key}-${i}`}>{inline(line)}</p>);
  }); flush(); return nodes;
}

export default function MarkdownContent({ content }: { content: string }) {
  return <>{content.split(/(```[\s\S]*?```)/g).map((part, index) => {
    if (!part.startsWith("```")) return textBlock(part, String(index));
    const [language = "", ...lines] = part.slice(3, -3).split("\n"); const code = lines.join("\n");
    return <div className="code-block" key={index}><div className="code-toolbar"><span>{language || "code"}</span><button type="button" onClick={() => copyCode(code)}>Copy Code</button></div><pre><code>{code}</code></pre></div>;
  })}</>;
}
