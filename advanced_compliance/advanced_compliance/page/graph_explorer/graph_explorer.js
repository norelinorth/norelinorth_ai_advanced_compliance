frappe.pages["graph-explorer"].on_page_load = function (wrapper) {
  var page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Compliance Graph Explorer"),
    single_column: true,
  });

  // Load vis.js from CDN
  frappe.require(
    ["https://unpkg.com/vis-network@9.1.2/standalone/umd/vis-network.min.js"],
    function () {
      new GraphExplorer(page);
    },
  );
};

class GraphExplorer {
  constructor(page) {
    this.page = page;
    this.network = null;
    this.nodes = null;
    this.edges = null;
    this.selected_entity = null;

    this.setup_page();
    this.setup_filters();
    this.setup_graph_container();
    this.setup_details_panel();
    this.load_graph();
  }

  setup_page() {
    // Add page actions
    this.page.set_primary_action(
      __("Refresh"),
      () => this.load_graph(),
      "refresh",
    );

    this.page.add_menu_item(__("Rebuild Graph"), () => this.rebuild_graph());
    this.page.add_menu_item(__("Export as Image"), () => this.export_image());
    this.page.add_menu_item(__("View Statistics"), () =>
      this.show_statistics(),
    );
  }

  setup_filters() {
    // Entity type filter
    this.entity_type_filter = this.page.add_field({
      fieldname: "entity_type",
      label: __("Entity Type"),
      fieldtype: "Select",
      options: [
        "",
        "Control",
        "Risk",
        "Person",
        "Process",
        "Evidence",
        "Requirement",
        "Objective",
        "System",
        "Department",
        "Company",
        "Document",
        "Period",
      ].join("\n"),
      change: () => this.load_graph(),
    });

    // Depth filter
    this.depth_filter = this.page.add_field({
      fieldname: "depth",
      label: __("Depth"),
      fieldtype: "Select",
      options: "1\n2\n3\n4\n5",
      default: "2",
      change: () => this.load_graph(),
    });

    // Max nodes filter
    this.max_nodes_filter = this.page.add_field({
      fieldname: "max_nodes",
      label: __("Max Nodes"),
      fieldtype: "Select",
      options: "25\n50\n100\n200",
      default: "100",
      change: () => this.load_graph(),
    });

    // Center entity
    this.center_entity_filter = this.page.add_field({
      fieldname: "center_entity",
      label: __("Center Entity"),
      fieldtype: "Link",
      options: "Compliance Graph Entity",
      change: () => this.load_graph(),
    });
  }

  setup_graph_container() {
    // Create main container
    this.page.$main_section = $(this.page.main);
    this.page.$main_section.html(`
            <div class="graph-explorer-container">
                <div class="row">
                    <div class="col-md-9">
                        <div class="graph-wrapper">
                            <div id="graph-container" style="height: 600px; border: 1px solid #d1d8dd; border-radius: 4px;"></div>
                        </div>
                        <div class="graph-legend mt-3">
                            <h6>${__("Legend")}</h6>
                            <div class="legend-items d-flex flex-wrap"></div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="details-panel">
                            <h5>${__("Entity Details")}</h5>
                            <div id="entity-details" class="p-3 border rounded">
                                <p class="text-muted">${__(
                                  "Click on a node to see details",
                                )}</p>
                            </div>
                            <div class="mt-3">
                                <h5>${__("Relationships")}</h5>
                                <div id="entity-relationships" class="p-3 border rounded">
                                    <p class="text-muted">${__(
                                      "Select an entity to see relationships",
                                    )}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `);

    // Build legend
    this.build_legend();
  }

  async build_legend() {
    // Entity type colors (must match ENTITY_COLORS in compliance_graph_entity.py)
    const colors = {
      Control: "#3498db", // Blue
      Risk: "#e74c3c", // Red
      Person: "#9b59b6", // Purple
      Evidence: "#f39c12", // Orange
      Department: "#e67e22", // Dark Orange
      Company: "#27ae60", // Dark Green
    };

    // Fetch actual entity types from database and build legend dynamically
    var self = this;
    try {
      const response = await frappe.call({
        method: "frappe.client.get_list",
        args: {
          doctype: "Compliance Graph Entity",
          filters: { is_active: 1 },
          fields: ["entity_type"],
          group_by: "entity_type",
          limit_page_length: 0,
        },
      });

      let legend_html = "";
      if (response.message && response.message.length > 0) {
        const actual_types = [
          ...new Set(response.message.map((e) => e.entity_type)),
        ];
        for (const type of actual_types) {
          const color = colors[type] || "#7f8c8d";
          legend_html += `
                          <div class="legend-item mr-3 mb-2">
                              <span class="legend-color" style="background-color: ${color}; width: 12px; height: 12px; display: inline-block; border-radius: 50%; margin-right: 4px;"></span>
                              <span class="legend-label">${__(type)}</span>
                          </div>
                      `;
        }
      }
      if (!legend_html) {
        legend_html =
          '<span class="text-muted">' +
          __("No entities in graph. Click Menu → Rebuild Graph.") +
          "</span>";
      }
      self.page.$main_section.find(".legend-items").html(legend_html);
    } catch (error) {
      // If legend fetch fails, show default message
      const legend_html =
        '<span class="text-muted">' +
        __("Unable to load legend. Click Menu → Rebuild Graph.") +
        "</span>";
      self.page.$main_section.find(".legend-items").html(legend_html);
    }
  }

  setup_details_panel() {
    // Already set up in the main container
  }

  async load_graph() {
    const entity_type = this.entity_type_filter.get_value();
    const depth = this.depth_filter.get_value() || 2;
    const max_nodes = this.max_nodes_filter.get_value() || 100;
    const center_entity = this.center_entity_filter.get_value();

    try {
      const data = await frappe.call({
        method:
          "advanced_compliance.advanced_compliance.knowledge_graph.query.get_visualization_data",
        args: {
          entity_type: entity_type || null,
          center_entity: center_entity || null,
          depth: depth,
          max_nodes: max_nodes,
        },
      });

      if (data.message) {
        await this.render_graph(data.message);
      }
    } catch (e) {
      console.error("Failed to load graph:", e);
      frappe.msgprint({
        title: __("Error"),
        indicator: "red",
        message: __("Failed to load graph data"),
      });
    }
  }

  render_graph(data) {
    return new Promise((resolve, reject) => {
      try {
        const container = document.getElementById("graph-container");

        // Create datasets
        this.nodes = new vis.DataSet(data.nodes);
        this.edges = new vis.DataSet(data.edges);

        // Network options with physics enabled for nice layout
        const options = {
          nodes: {
            shape: "dot",
            scaling: {
              min: 10,
              max: 30,
            },
            font: {
              size: 12,
              face: "Inter, -apple-system, system-ui, sans-serif",
            },
          },
          edges: {
            width: 1,
            color: { inherit: "from" },
            smooth: {
              type: "continuous",
            },
            arrows: {
              to: { enabled: true, scaleFactor: 0.5 },
            },
          },
          physics: {
            enabled: true,
            stabilization: {
              enabled: true,
              iterations: 100,
              updateInterval: 25,
            },
            barnesHut: {
              gravitationalConstant: -2000,
              springLength: 150,
              springConstant: 0.04,
            },
          },
          interaction: {
            hover: true,
            tooltipDelay: 200,
            hideEdgesOnDrag: true,
          },
        };

        // Create network
        this.network = new vis.Network(
          container,
          { nodes: this.nodes, edges: this.edges },
          options,
        );

        // Wait for physics stabilization, with timeout fallback
        let resolved = false;

        this.network.once("stabilizationIterationsDone", () => {
          if (!resolved) {
            resolved = true;
            resolve();
          }
        });

        // Fallback: resolve after 3 seconds even if stabilization doesn't complete
        setTimeout(() => {
          if (!resolved) {
            resolved = true;
            resolve();
          }
        }, 3000);

        // Event handlers
        this.network.on("click", (params) => {
          if (params.nodes.length > 0) {
            this.on_node_click(params.nodes[0]);
          } else if (params.edges.length > 0) {
            this.on_edge_click(params.edges[0]);
          } else {
            this.clear_selection();
          }
        });

        this.network.on("doubleClick", (params) => {
          if (params.nodes.length > 0) {
            this.on_node_double_click(params.nodes[0]);
          }
        });

        // Update node count
        this.page.set_secondary_action(
          `${data.node_count} ${__("nodes")}, ${data.edge_count} ${__(
            "edges",
          )}`,
          null,
          "info-sign",
        );
      } catch (err) {
        console.error("Error rendering graph:", err);
        reject(err);
      }
    });
  }

  async on_node_click(node_id) {
    this.selected_entity = node_id;
    const node = this.nodes.get(node_id);

    // Show entity details
    const details_html = `
            <div class="entity-info">
                <h6 style="color: ${node.color}">${node.label}</h6>
                <table class="table table-sm">
                    <tr><td><strong>${__("ID")}</strong></td><td>${
                      node.id
                    }</td></tr>
                    <tr><td><strong>${__("Type")}</strong></td><td>${
                      node.group || "-"
                    }</td></tr>
                </table>
                <button class="btn btn-xs btn-primary" onclick="cur_page.explorer.open_entity('${node_id}')">
                    ${__("Open")}
                </button>
            </div>
        `;
    $("#entity-details").html(details_html);

    // Fetch relationships
    try {
      const rel_data = await frappe.call({
        method:
          "advanced_compliance.advanced_compliance.knowledge_graph.query.get_entity_neighbors",
        args: {
          entity_name: node_id,
          direction: "both",
          max_depth: 1,
        },
      });

      if (rel_data.message) {
        this.show_relationships(rel_data.message);
      }
    } catch (e) {
      console.error("Failed to load relationships", e);
    }

    // Store reference for buttons
    if (!window.cur_page) window.cur_page = {};
    window.cur_page.explorer = this;
  }

  show_relationships(relationships) {
    if (!relationships.length) {
      $("#entity-relationships").html(
        `<p class="text-muted">${__("No relationships found")}</p>`,
      );
      return;
    }

    let html = '<ul class="list-unstyled mb-0">';
    for (const rel of relationships) {
      const direction_icon = rel.direction === "outgoing" ? "&rarr;" : "&larr;";
      html += `
                <li class="mb-2">
                    <span class="badge badge-secondary">${rel.relationship_type}</span>
                    ${direction_icon}
                    <a href="#" onclick="cur_page.explorer.focus_entity('${rel.entity}'); return false;">
                        ${rel.entity}
                    </a>
                </li>
            `;
    }
    html += "</ul>";
    $("#entity-relationships").html(html);
  }

  on_node_double_click(node_id) {
    // Center graph on this node
    this.center_entity_filter.set_value(node_id);
    this.load_graph();
  }

  on_edge_click(edge_id) {
    const edge = this.edges.get(edge_id);
    if (edge) {
      $("#entity-details").html(`
                <div class="edge-info">
                    <h6>${__("Relationship")}</h6>
                    <table class="table table-sm">
                        <tr><td><strong>${__("Type")}</strong></td><td>${
                          edge.label || "-"
                        }</td></tr>
                        <tr><td><strong>${__("From")}</strong></td><td>${
                          edge.from
                        }</td></tr>
                        <tr><td><strong>${__("To")}</strong></td><td>${
                          edge.to
                        }</td></tr>
                    </table>
                </div>
            `);
    }
  }

  clear_selection() {
    this.selected_entity = null;
    $("#entity-details").html(
      `<p class="text-muted">${__("Click on a node to see details")}</p>`,
    );
    $("#entity-relationships").html(
      `<p class="text-muted">${__(
        "Select an entity to see relationships",
      )}</p>`,
    );
  }

  open_entity(entity_name) {
    frappe.set_route("Form", "Compliance Graph Entity", entity_name);
  }

  focus_entity(entity_name) {
    if (this.network) {
      this.network.focus(entity_name, {
        scale: 1.5,
        animation: {
          duration: 500,
          easingFunction: "easeInOutQuad",
        },
      });
      this.network.selectNodes([entity_name]);
      this.on_node_click(entity_name);
    }
  }

  async rebuild_graph() {
    frappe.confirm(
      __(
        "This will rebuild the entire knowledge graph from scratch. Continue?",
      ),
      async () => {
        frappe.show_progress(__("Rebuilding Graph"), 0, 100, __("Starting..."));

        try {
          const result = await frappe.call({
            method:
              "advanced_compliance.advanced_compliance.knowledge_graph.sync.rebuild_graph",
          });

          frappe.hide_progress();

          if (result.message) {
            frappe.msgprint({
              title: __("Graph Rebuilt"),
              indicator: "green",
              message: __("Created {0} entities and {1} relationships", [
                result.message.entities,
                result.message.relationships,
              ]),
            });
            this.load_graph();
          }
        } catch (e) {
          frappe.hide_progress();
          frappe.msgprint({
            title: __("Error"),
            indicator: "red",
            message: __("Failed to rebuild graph"),
          });
        }
      },
    );
  }

  export_image() {
    if (!this.network) {
      frappe.msgprint(__("No graph to export"));
      return;
    }

    // Get canvas and convert to image
    const canvas = document.querySelector("#graph-container canvas");
    if (canvas) {
      const dataUrl = canvas.toDataURL("image/png");
      const link = document.createElement("a");
      link.download = "compliance-graph.png";
      link.href = dataUrl;
      link.click();
    }
  }

  async show_statistics() {
    try {
      const stats = await frappe.call({
        method:
          "advanced_compliance.advanced_compliance.knowledge_graph.query.get_graph_statistics",
      });

      if (stats.message) {
        const s = stats.message;
        let entity_breakdown = "";
        for (const [type, count] of Object.entries(s.entities_by_type)) {
          entity_breakdown += `<li>${type}: ${count}</li>`;
        }

        let rel_breakdown = "";
        for (const [type, count] of Object.entries(s.relationships_by_type)) {
          rel_breakdown += `<li>${type}: ${count}</li>`;
        }

        const dialog = new frappe.ui.Dialog({
          title: __("Graph Statistics"),
          size: "large",
          fields: [
            {
              fieldtype: "HTML",
              options: `
                            <div class="row">
                                <div class="col-md-4 text-center">
                                    <h2>${s.total_entities}</h2>
                                    <p class="text-muted">${__("Entities")}</p>
                                </div>
                                <div class="col-md-4 text-center">
                                    <h2>${s.total_relationships}</h2>
                                    <p class="text-muted">${__(
                                      "Relationships",
                                    )}</p>
                                </div>
                                <div class="col-md-4 text-center">
                                    <h2>${s.total_paths}</h2>
                                    <p class="text-muted">${__(
                                      "Computed Paths",
                                    )}</p>
                                </div>
                            </div>
                            <hr>
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>${__("Entities by Type")}</h6>
                                    <ul>${
                                      entity_breakdown || "<li>No entities</li>"
                                    }</ul>
                                </div>
                                <div class="col-md-6">
                                    <h6>${__("Relationships by Type")}</h6>
                                    <ul>${
                                      rel_breakdown ||
                                      "<li>No relationships</li>"
                                    }</ul>
                                </div>
                            </div>
                        `,
            },
          ],
        });
        dialog.show();
      }
    } catch (e) {
      frappe.msgprint({
        title: __("Error"),
        indicator: "red",
        message: __("Failed to load statistics"),
      });
    }
  }
}
