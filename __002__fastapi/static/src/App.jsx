const { useState, useCallback } = React;

const API_PATH = "/receive_raw_json/";
const APPROVE_PATH = "/approve_workflow/";
const REQUEST_TIMEOUT_MS = 600000;

const EXAMPLES = ["湖北荆州", "都江堰", "新疆天山", "呼和浩特"];

const IMAGE_SOURCES = [
  {
    value: "ai",
    label: "AI 生图",
    desc: "调用百炼大模型生成 1 张旅行配图",
    icon: "🎨",
  },
  {
    value: "baidu",
    label: "百度爬虫",
    desc: "按「地点 + 旅行」搜索并下载，最多 4 张",
    icon: "🔍",
  },
];

function asBool(value) {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") {
    return ["true", "1", "yes"].includes(value.trim().toLowerCase());
  }
  return Boolean(value);
}

const styles = {
  page: {
    minHeight: "100vh",
    background:
      "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.35), transparent)," +
      "radial-gradient(ellipse 60% 40% at 100% 50%, rgba(236, 72, 153, 0.12), transparent)," +
      "radial-gradient(ellipse 50% 30% at 0% 80%, rgba(34, 211, 238, 0.1), transparent)," +
      "#0f1419",
    padding: "32px 20px 64px",
  },
  container: { maxWidth: 960, margin: "0 auto" },
  header: { textAlign: "center", marginBottom: 40 },
  badge: {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    padding: "6px 14px",
    borderRadius: 999,
    background: "rgba(99, 102, 241, 0.15)",
    border: "1px solid rgba(129, 140, 248, 0.35)",
    color: "#a5b4fc",
    fontSize: 13,
    fontWeight: 500,
    marginBottom: 16,
  },
  title: {
    fontSize: "clamp(1.75rem, 4vw, 2.5rem)",
    fontWeight: 700,
    background: "linear-gradient(135deg, #f8fafc 0%, #c7d2fe 50%, #fda4af 100%)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
    letterSpacing: "-0.02em",
    lineHeight: 1.25,
  },
  subtitle: { marginTop: 12, color: "#94a3b8", fontSize: 15, lineHeight: 1.6 },
  card: {
    background: "rgba(30, 41, 59, 0.55)",
    backdropFilter: "blur(16px)",
    WebkitBackdropFilter: "blur(16px)",
    border: "1px solid rgba(148, 163, 184, 0.12)",
    borderRadius: 20,
    padding: "28px 24px",
    boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.45)",
  },
  label: { display: "block", fontSize: 14, fontWeight: 600, color: "#cbd5e1", marginBottom: 10 },
  inputRow: { display: "flex", gap: 12, flexWrap: "wrap" },
  input: {
    flex: "1 1 240px",
    padding: "14px 18px",
    fontSize: 16,
    borderRadius: 12,
    border: "1px solid rgba(148, 163, 184, 0.2)",
    background: "rgba(15, 23, 42, 0.6)",
    color: "#f1f5f9",
    outline: "none",
    transition: "border-color 0.2s, box-shadow 0.2s",
  },
  btnPrimary: {
    flex: "0 0 auto",
    padding: "14px 28px",
    fontSize: 16,
    fontWeight: 600,
    borderRadius: 12,
    border: "none",
    cursor: "pointer",
    background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%)",
    color: "#fff",
    boxShadow: "0 4px 20px rgba(99, 102, 241, 0.45)",
    transition: "transform 0.15s, opacity 0.2s, box-shadow 0.2s",
    minWidth: 140,
  },
  btnDisabled: { opacity: 0.45, cursor: "not-allowed", boxShadow: "none" },
  chips: { display: "flex", flexWrap: "wrap", gap: 8, marginTop: 16 },
  chip: {
    padding: "6px 14px",
    fontSize: 13,
    borderRadius: 999,
    border: "1px solid rgba(148, 163, 184, 0.2)",
    background: "rgba(15, 23, 42, 0.5)",
    color: "#94a3b8",
    cursor: "pointer",
    transition: "all 0.15s",
  },
  chipHover: { borderColor: "rgba(129, 140, 248, 0.5)", color: "#c7d2fe" },
  steps: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
    gap: 12,
    marginTop: 28,
    marginBottom: 8,
  },
  step: {
    padding: "14px 12px",
    borderRadius: 12,
    background: "rgba(15, 23, 42, 0.4)",
    border: "1px solid rgba(148, 163, 184, 0.08)",
    textAlign: "center",
    fontSize: 13,
    color: "#64748b",
  },
  stepIcon: { fontSize: 22, marginBottom: 6 },
  loading: {
    marginTop: 28,
    padding: 24,
    borderRadius: 16,
    background: "rgba(99, 102, 241, 0.08)",
    border: "1px solid rgba(99, 102, 241, 0.2)",
    display: "flex",
    alignItems: "center",
    gap: 16,
  },
  spinner: {
    width: 28,
    height: 28,
    border: "3px solid rgba(129, 140, 248, 0.25)",
    borderTopColor: "#818cf8",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  alert: {
    marginTop: 24,
    padding: "16px 20px",
    borderRadius: 14,
    fontSize: 15,
    lineHeight: 1.5,
  },
  alertSuccess: {
    background: "rgba(34, 197, 94, 0.12)",
    border: "1px solid rgba(34, 197, 94, 0.35)",
    color: "#86efac",
  },
  alertError: {
    background: "rgba(239, 68, 68, 0.12)",
    border: "1px solid rgba(239, 68, 68, 0.35)",
    color: "#fca5a5",
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 600,
    color: "#e2e8f0",
    marginTop: 32,
    marginBottom: 16,
    paddingBottom: 8,
    borderBottom: "1px solid rgba(148, 163, 184, 0.12)",
  },
  previewWrap: {
    marginTop: 8,
    borderRadius: 16,
    overflow: "hidden",
    border: "1px solid rgba(148, 163, 184, 0.15)",
    background: "#fff",
    minHeight: 200,
  },
  previewFrame: { width: "100%", height: 720, border: "none", display: "block" },
  footer: {
    marginTop: 48,
    textAlign: "center",
    fontSize: 13,
    color: "#475569",
  },
};

function StatusAlert({ success, message }) {
  const style = {
    ...styles.alert,
    ...(success ? styles.alertSuccess : styles.alertError),
  };
  return (
    <div style={style} role="alert">
      {success ? "✓ " : "✕ "}
      {message}
    </div>
  );
}

function App() {
  const [userInput, setUserInput] = useState("");
  const [imageSource, setImageSource] = useState("ai");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [pendingThreadId, setPendingThreadId] = useState(null);
  const [requireHumanApproval, setRequireHumanApproval] = useState(false);

  const imageSourceMeta =
    IMAGE_SOURCES.find((s) => s.value === imageSource) || IMAGE_SOURCES[0];

  const submit = useCallback(async () => {
    const trimmed = userInput.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setPendingThreadId(null);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const res = await fetch(API_PATH, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_input: trimmed,
          image_source: imageSource,
          require_human_approval: requireHumanApproval,
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`请求失败（HTTP ${res.status}）`);
      }

      const data = await res.json();
      setResult(data);
      if (data.needs_approval && data.thread_id) {
        setPendingThreadId(data.thread_id);
      }
    } catch (err) {
      if (err.name === "AbortError") {
        setError("请求超时，工作流可能仍在运行，请稍后重试。");
      } else if (err.message.includes("Failed to fetch")) {
        setError("无法连接后端，请确认已启动：python __002__fastapi/__001__server.py");
      } else {
        setError(err.message || "请求异常");
      }
    } finally {
      clearTimeout(timer);
      setLoading(false);
    }
  }, [userInput, imageSource, requireHumanApproval, loading]);

  const submitApproval = useCallback(
    async (approval) => {
      if (!pendingThreadId || loading) return;
      setLoading(true);
      setError(null);
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
      try {
        const res = await fetch(APPROVE_PATH, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ thread_id: pendingThreadId, approval }),
          signal: controller.signal,
        });
        if (!res.ok) {
          throw new Error(`审核请求失败（HTTP ${res.status}）`);
        }
        const data = await res.json();
        setResult(data);
        setPendingThreadId(null);
      } catch (err) {
        if (err.name === "AbortError") {
          setError("审核请求超时，请稍后重试。");
        } else {
          setError(err.message || "审核请求异常");
        }
      } finally {
        clearTimeout(timer);
        setLoading(false);
      }
    },
    [pendingThreadId, loading]
  );

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const needsApproval = Boolean(result?.needs_approval && pendingThreadId);
  const isSuccess = result ? asBool(result.is_publish_success) : false;
  const outputMsg = result?.output || "（无提示信息）";
  const toutiaoHtml = result?.toutiao_html || "";

  return (
    <div style={styles.page}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <div style={styles.container}>
        <header style={styles.header}>
          <div style={styles.badge}>
            <span>📰</span>
            <span>LangGraph 工作流 · 头条自动营销</span>
          </div>
          <h1 style={styles.title}>自动营销助手</h1>
          <p style={styles.subtitle}>
            输入旅游/营销主题，生成文案与配图；可勾选「发布前人工审核」，未勾选则校验通过后直接发布。
          </p>
        </header>

        <div style={styles.card}>
          <label style={styles.label} htmlFor="topic-input">
            营销主题
          </label>
          <div style={styles.inputRow}>
            <input
              id="topic-input"
              type="text"
              style={styles.input}
              placeholder="例如：湖北荆州、都江堰、新疆天山"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={loading}
              onFocus={(e) => {
                e.target.style.borderColor = "rgba(129, 140, 248, 0.6)";
                e.target.style.boxShadow = "0 0 0 3px rgba(99, 102, 241, 0.2)";
              }}
              onBlur={(e) => {
                e.target.style.borderColor = "rgba(148, 163, 184, 0.2)";
                e.target.style.boxShadow = "none";
              }}
            />
            <button
              type="button"
              style={{
                ...styles.btnPrimary,
                ...((!userInput.trim() || loading) ? styles.btnDisabled : {}),
              }}
              disabled={!userInput.trim() || loading}
              onClick={submit}
              onMouseEnter={(e) => {
                if (!e.currentTarget.disabled) e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "none";
              }}
            >
              {loading ? "处理中…" : "开始处理"}
            </button>
          </div>

          <label style={{ ...styles.label, marginTop: 24 }}>配图方式</label>
          <div className="image-source-group" role="radiogroup" aria-label="配图方式">
            {IMAGE_SOURCES.map((opt) => {
              const selected = imageSource === opt.value;
              return (
                <label
                  key={opt.value}
                  className={
                    "image-source-option" +
                    (selected ? " is-selected" : "") +
                    (loading ? " is-disabled" : "")
                  }
                >
                  <input
                    type="radio"
                    name="image_source"
                    value={opt.value}
                    checked={selected}
                    disabled={loading}
                    onChange={() => setImageSource(opt.value)}
                  />
                  <div className="option-body">
                    <div className="option-title">
                      {opt.icon} {opt.label}
                    </div>
                    <div className="option-desc">{opt.desc}</div>
                  </div>
                </label>
              );
            })}
          </div>

          <label
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 12,
              marginTop: 20,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.6 : 1,
            }}
          >
            <input
              type="checkbox"
              checked={requireHumanApproval}
              disabled={loading}
              onChange={(e) => setRequireHumanApproval(e.target.checked)}
              style={{ marginTop: 4, accentColor: "#818cf8", flexShrink: 0 }}
            />
            <span>
              <span style={{ display: "block", fontSize: 15, fontWeight: 600, color: "#e2e8f0" }}>
                发布前人工审核
              </span>
              <span style={{ display: "block", fontSize: 13, color: "#94a3b8", marginTop: 4, lineHeight: 1.45 }}>
                勾选后先生成预览，确认后再发布；不勾选则校验通过后自动发布到头条。
              </span>
            </span>
          </label>

          <div style={styles.chips}>
            <span style={{ fontSize: 13, color: "#64748b", alignSelf: "center", marginRight: 4 }}>
              试试：
            </span>
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                style={styles.chip}
                disabled={loading}
                onClick={() => setUserInput(ex)}
                onMouseEnter={(e) => Object.assign(e.currentTarget.style, styles.chipHover)}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "rgba(148, 163, 184, 0.2)";
                  e.currentTarget.style.color = "#94a3b8";
                }}
              >
                {ex}
              </button>
            ))}
          </div>

          <div style={styles.steps}>
            {[
              { icon: "✍️", text: "文案生成" },
              {
                icon: imageSourceMeta.icon,
                text: imageSource === "baidu" ? "百度配图" : "AI 配图",
              },
              { icon: "✅", text: "图文校验" },
              { icon: "👁️", text: "预览 HTML" },
              ...(requireHumanApproval ? [{ icon: "👤", text: "人工审核" }] : []),
              { icon: "🚀", text: "头条发布" },
            ].map((s) => (
              <div key={s.text} style={styles.step}>
                <div style={styles.stepIcon}>{s.icon}</div>
                {s.text}
              </div>
            ))}
          </div>

          {loading && (
            <div style={styles.loading}>
              <div style={styles.spinner} />
              <div>
                <div style={{ fontWeight: 600, color: "#c7d2fe" }}>工作流运行中</div>
                <div style={{ fontSize: 14, color: "#94a3b8", marginTop: 4 }}>
                  正在生成文案，使用「{imageSourceMeta.label}」获取配图
                  {requireHumanApproval ? "，完成后等待您审核…" : "并发布到头条…"}
                </div>
              </div>
            </div>
          )}
        </div>

        {error && <StatusAlert success={false} message={error} />}

        {result && (
          <>
            {needsApproval ? (
              <div
                style={{
                  ...styles.alert,
                  background: "rgba(251, 191, 36, 0.12)",
                  border: "1px solid rgba(251, 191, 36, 0.35)",
                  color: "#fcd34d",
                }}
                role="status"
              >
                文案与配图已生成，请预览后确认是否发布到头条。
              </div>
            ) : (
              <StatusAlert
                success={isSuccess}
                message={isSuccess ? `发布成功：${outputMsg}` : `发布未成功：${outputMsg}`}
              />
            )}

            {needsApproval && (
              <div style={{ ...styles.inputRow, marginTop: 16 }}>
                <button
                  type="button"
                  style={{ ...styles.btnPrimary, minWidth: 160 }}
                  disabled={loading}
                  onClick={() => submitApproval("批准")}
                >
                  批准并发布
                </button>
                <button
                  type="button"
                  style={{
                    ...styles.btnPrimary,
                    minWidth: 160,
                    background: "linear-gradient(135deg, #64748b 0%, #475569 100%)",
                    boxShadow: "none",
                  }}
                  disabled={loading}
                  onClick={() => submitApproval("不批准")}
                >
                  拒绝发布
                </button>
              </div>
            )}

            {toutiaoHtml ? (
              <>
                <h2 style={styles.sectionTitle}>图文预览</h2>
                <div style={styles.previewWrap}>
                  <iframe
                    title="头条图文预览"
                    style={styles.previewFrame}
                    srcDoc={toutiaoHtml}
                    sandbox="allow-same-origin"
                  />
                </div>
              </>
            ) : (
              <div style={{ ...styles.alert, ...styles.alertError, marginTop: 24 }}>
                未生成 HTML 预览内容，请查看服务端日志后重试。
              </div>
            )}
          </>
        )}

        <footer style={styles.footer}>
          启动服务后访问 <strong style={{ color: "#94a3b8" }}>http://127.0.0.1:8000</strong> · API{" "}
          <code style={{ color: "#818cf8" }}>POST /receive_raw_json/</code> ·{" "}
          <code style={{ color: "#818cf8" }}>POST /approve_workflow/</code>
        </footer>
      </div>
    </div>
  );
}

const rootEl = document.getElementById("root");
if (ReactDOM.createRoot) {
  ReactDOM.createRoot(rootEl).render(<App />);
} else {
  ReactDOM.render(<App />, rootEl);
}
