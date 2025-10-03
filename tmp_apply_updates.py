from pathlib import Path
from textwrap import dedent

tsx_path = Path("Frontend/src/app/components/HUD/TokenTrackingPanel.tsx")
text = tsx_path.read_text(encoding="utf-8")

metrics_start = text.index("  const renderTokenMetrics = () => {")
metrics_end = text.index("  // REAL DATA AGENT LIST", metrics_start)
text = text[:metrics_start] + dedent('''
  const renderTokenMetrics = () => {
    if (!tokenData) return null;

    const totalTokens = tokenData.total_tokens || 0;
    const totalCost = tokenData.total_cost_usd || 0;

    const summary = [
      {
        label: "Total Tokens",
        value: formatNumber(totalTokens),
        icon: "TT",
      },
      {
        label: "Total Cost",
        value: formatCurrency(totalCost),
        icon: "",
        iconSymbol: "",
      },
    ];

    return (
      <nav className={styles.metricsNav} aria-label="Token metrics summary">
        <ul className={navStyles.navigatorList}>
          <li className={navStyles.navigatorItem}>
            <div className={navStyles.navigatorButton} role="presentation">
              <span className={navStyles.navigatorIcon} aria-hidden="true">
                <span className={styles.iconText}>TT</span>
              </span>
              <span className={navStyles.navigatorLabel}>
                <span className={styles.metricLabel}>Total Tokens</span>
                <span className={styles.metricValue}>
                  {formatNumber(totalTokens)}
                </span>
              </span>
            </div>
          </li>
          <li className={navStyles.navigatorItem}>
            <div className={navStyles.navigatorButton} role="presentation">
              <span className={navStyles.navigatorIcon} aria-hidden="true">
                <span className={styles.iconText}>$</span>
              </span>
              <span className={navStyles.navigatorLabel}>
                <span className={styles.metricLabel}>Total Cost</span>
                <span className={styles.metricValue}>
                  {formatCurrency(totalCost)}
                </span>
              </span>
            </div>
          </li>
        </ul>
      </nav>
    );
  };


''') + text[metrics_end:]

agent_start = text.index("  // REAL DATA AGENT LIST\n")
agent_end = text.index("  // Cost timeline visualization", agent_start)
text = text[:agent_start] + dedent('''  // REAL DATA AGENT LIST
  const renderAgentBreakdown = () => {
    if (!tokenData?.agents || typeof tokenData.agents !== "object") return null;

    const agentsArray = Object.entries(tokenData.agents).map(
      ([name, data]: [string, any]) => ({
        name,
        total_tokens: data.total_tokens || 0,
        prompt_tokens: data.prompt_tokens_total || data.prompt_tokens || 0,
        completion_tokens:
          data.completion_tokens_total || data.completion_tokens || 0,
        cost_usd: data.cost_usd || 0,
        status: data.status || "idle",
        provider: data.provider || "openai",
        last_model: data.last_model || null,
        last_seen: data.last_seen || null,
      }),
    );

    if (agentsArray.length === 0) {
      return <p className={styles.emptyState}>No agent metrics available.</p>;
    }

    const sortedAgents = agentsArray.sort(
      (a, b) => b.total_tokens - a.total_tokens,
    );
    const topAgentName = sortedAgents[0]?.name ?? null;

    return (
      <section className={styles.agentSection} aria-label="Agent breakdown">
        <h4 className={styles.sectionTitle}>Agent Breakdown</h4>
        <div className={styles.agentNavList}>
          {sortedAgents.map((agent) => {
            const isTopAgent = agent.name === topAgentName;
            const buttonClass = [
              navStyles.navigatorButton,
              styles.agentNavButton,
              isTopAgent ? navStyles.navigatorButtonActive : "",
            ]
              .filter(Boolean)
              .join(" ");

            return (
              <div key={agent.name} className={styles.agentNavItem}>
                <div className={buttonClass} role="presentation">
                  <span
                    className={navStyles.navigatorIcon}
                    style={{
                      backgroundColor: resolveAgentColor(agent.name),
                      boxShadow: `0 0 8px ${resolveAgentColor(agent.name)}47`,
                    }}
                    aria-hidden="true"
                  />
                  <span
                    className={`${navStyles.navigatorLabel} ${styles.agentLabelGroup}`}
                  >
                    <span className={styles.agentName}>{agent.name}</span>
                    <span className={styles.agentMetricsLine}>
                      <span className={styles.agentMetric}>
                        {formatNumber(agent.total_tokens)} tokens
                      </span>
                      <span className={styles.agentMetric}>
                        {formatCurrency(agent.cost_usd)}
                      </span>
                      <span className={styles.agentMetric}>
                        in {formatNumber(agent.prompt_tokens)} / out {""}
                        {formatNumber(agent.completion_tokens)}
                      </span>
                    </span>
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    );
  };


''') + text[agent_end:]

tsx_path.write_text(text, encoding="utf-8")

css_path = Path("Frontend/src/app/components/HUD/TokenTrackingPanel.module.css")
css = css_path.read_text(encoding="utf-8")
start_css = css.index("/* ==========================================\n   HUD NAVIGATOR REPLICA BLOCKS")
end_css = css.index(".agentMetric {", start_css)
end_css = css.index("}\n", end_css) + 1
css = css[:start_css] + dedent('''/* ==========================================
   HUD NAVIGATOR REPLICA BLOCKS
   ========================================== */
.metricsNav {
  display: flex;
  justify-content: center;
  margin: clamp(4px, 0.9vw, 8px) 0;
}

.metricsLabelGroup {
  display: flex;
  flex-direction: column;
  gap: clamp(2px, 0.4vw, 4px);
  letter-spacing: inherit;
  text-transform: inherit;
  align-items: flex-start;
}

.iconText {
  font-size: clamp(8px, 0.75vw, 10px);
  font-weight: 600;
  letter-spacing: 0.14em;
}

.metricsLabel {
  font-size: clamp(9px, 0.85vw, 11px);
  letter-spacing: inherit;
  text-transform: inherit;
  color: rgba(226, 232, 240, 0.78);
}

.metricsValue {
  font-size: clamp(18px, 2.4vw, 28px);
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #e0f2fe;
  text-shadow: 0 0 16px rgba(96, 202, 255, 0.35);
  line-height: 1.1;
}

.agentSection {
  display: flex;
  flex-direction: column;
  gap: clamp(12px, 1.4vw, 18px);
  margin-top: clamp(12px, 1.4vw, 20px);
}

.sectionTitle {
  margin: 0;
  font-size: clamp(10px, 1.1vw, 12px);
  text-transform: uppercase;
  letter-spacing: 0.22em;
  color: #7df9ff;
  text-shadow: 0 0 12px rgba(96, 202, 255, 0.45);
}

.agentNavList {
  display: flex;
  flex-direction: column;
  gap: clamp(4px, 0.75vw, 9px);
  width: 100%;
  align-items: stretch;
}

.agentNavItem {
  display: flex;
}

.agentNavButton {
  width: 100%;
  display: inline-flex;
  align-items: flex-start;
  justify-content: flex-start;
  gap: clamp(8px, 1vw, 12px);
  flex-wrap: wrap;
  cursor: default;
}

.agentLabelGroup {
  display: flex;
  flex-direction: column;
  gap: clamp(4px, 0.6vw, 8px);
  letter-spacing: inherit;
  text-transform: inherit;
  align-items: flex-start;
  color: rgba(226, 232, 240, 0.9);
}

.agentName {
  font-size: clamp(9px, 0.9vw, 11px);
  font-weight: 600;
  letter-spacing: inherit;
}

.agentMetricsLine {
  display: flex;
  flex-wrap: wrap;
  gap: clamp(6px, 0.8vw, 12px);
  font-size: clamp(8px, 0.75vw, 10px);
  letter-spacing: 0.12em;
  color: rgba(148, 233, 255, 0.72);
}

.agentMetric {
  display: inline-flex;
  align-items: center;
}
''') + css[end_css:]
css_path.write_text(css, encoding="utf-8")
