import { useEffect, useState } from "react";
import { getWorkspaceDirectory } from "../../services/api";
import type { ExplorerDirectory, ExplorerEntry } from "../../services/api";

function sizeLabel(size: number | null) {
  return size === null ? "—" : `${size.toLocaleString()} bytes`;
}

function displayPath(path: string) {
  return path === "" || path === "." ? "/" : `/${path}`;
}

export default function Explorer() {
  const [directory, setDirectory] = useState<ExplorerDirectory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDirectory = async (path = "") => {
    setLoading(true);
    setError("");
    try {
      setDirectory(await getWorkspaceDirectory(path));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load workspace contents.");
      setDirectory(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDirectory();
  }, []);

  const openEntry = (entry: ExplorerEntry) => {
    if (entry.is_directory) {
      void loadDirectory(entry.path);
    }
  };

  const goUp = () => {
    const parentPath = directory?.parent_path;
    if (parentPath !== null && parentPath !== undefined) {
      void loadDirectory(parentPath);
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1>Explorer</h1>
        <p>Browse your authenticated workspace content securely.</p>
      </header>
      {error && <p className="chat-error">{error}</p>}
      <div className="explorer-toolbar">
        <button type="button" onClick={() => void loadDirectory()} disabled={loading}>
          Refresh
        </button>
        <button type="button" onClick={goUp} disabled={loading || !directory?.parent_path}>
          Up
        </button>
        <span className="explorer-path">{displayPath(directory?.path ?? "")}</span>
      </div>
      {loading && <p>Loading workspace files…</p>}
      {!loading && directory && (
        <table className="explorer-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Size</th>
              <th>Modified</th>
            </tr>
          </thead>
          <tbody>
            {directory.entries.map((entry) => (
              <tr
                key={entry.path}
                className={entry.is_directory ? "explorer-directory" : "explorer-file"}
                onClick={() => openEntry(entry)}
                style={{ cursor: entry.is_directory ? "pointer" : "default" }}
              >
                <td>{entry.name}</td>
                <td>{entry.is_directory ? "Folder" : "File"}</td>
                <td>{sizeLabel(entry.size)}</td>
                <td>{new Date(entry.modified_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!loading && directory?.entries.length === 0 && <p>This directory is empty.</p>}
    </div>
  );
}