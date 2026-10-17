import "./material-lineage.css";
export interface PropagationPathNode {
  type: string;
  label: string;
  href: string;
  state?: string;
  current?: boolean;
}

export function PropagationPath({
  title = "Propagation path",
  stages,
  listLabel,
}: {
  title?: string;
  stages: PropagationPathNode[][];
  listLabel?: string;
}) {
  return (
    <section className="propagation-path material-lineage" aria-label={title}>
      <h4>{title}</h4>
      <ol aria-label={listLabel}>
        {stages.map((nodes, index) => (
          <li
            key={`${String(index)}:${nodes.map(({ href }) => href).join(":")}`}
          >
            <div className="propagation-path-stage">
              {nodes.map((node) => (
                <a
                  className="propagation-path-node"
                  href={node.href}
                  aria-current={node.current ? "page" : undefined}
                  key={node.href}
                >
                  <span className="eyebrow">{node.type}</span>
                  <strong>{node.label}</strong>
                  {node.state && (
                    <small>
                      {node.state === "reversed" ? "Reversed" : node.state}
                    </small>
                  )}
                </a>
              ))}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
