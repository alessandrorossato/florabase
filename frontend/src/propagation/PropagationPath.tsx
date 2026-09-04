export interface PropagationPathNode {
  type: string;
  label: string;
  href: string;
  state?: string;
}

export function PropagationPath({
  title = "Propagation path",
  stages,
}: {
  title?: string;
  stages: PropagationPathNode[][];
}) {
  return (
    <section className="propagation-path" aria-label={title}>
      <h4>{title}</h4>
      <ol>
        {stages.map((nodes, index) => (
          <li
            key={`${String(index)}:${nodes.map(({ href }) => href).join(":")}`}
          >
            <div className="propagation-path-stage">
              {nodes.map((node) => (
                <a
                  className="propagation-path-node"
                  href={node.href}
                  key={node.href}
                >
                  <span className="eyebrow">{node.type}</span>
                  <strong>{node.label}</strong>
                  {node.state && <small>{node.state}</small>}
                </a>
              ))}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
