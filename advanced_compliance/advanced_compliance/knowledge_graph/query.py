"""
Graph Query Engine.

Provides graph traversal and query capabilities for the compliance knowledge graph.
Supports path finding, pattern matching, and neighborhood exploration.
"""

import json
from collections import deque

import frappe
from frappe import _
from frappe.utils import cint


class GraphQueryEngine:
	"""Engine for querying the compliance knowledge graph."""

	def __init__(self):
		"""Initialize the query engine."""
		self.visited = set()
		self.path_cache = {}

	def get_entity(self, entity_name):
		"""
		Get entity details.

		Args:
		    entity_name: Name of the entity

		Returns:
		    Entity document as dict or None
		"""
		if not frappe.db.exists("Compliance Graph Entity", entity_name):
			return None

		return frappe.get_doc("Compliance Graph Entity", entity_name).as_dict()

	def get_entity_by_document(self, doctype, docname):
		"""
		Get entity for a specific document.

		Args:
		    doctype: The DocType
		    docname: The document name

		Returns:
		    Entity document as dict or None
		"""
		entity_name = frappe.db.get_value(
			"Compliance Graph Entity",
			{"entity_doctype": doctype, "entity_id": docname, "is_active": 1},
			"name",
		)

		if not entity_name:
			return None

		return frappe.get_doc("Compliance Graph Entity", entity_name).as_dict()

	def get_neighbors(self, entity_name, relationship_types=None, direction="both", max_depth=1):
		"""
		Get neighboring entities.

		Args:
		    entity_name: Starting entity name
		    relationship_types: Optional list of relationship types to filter
		    direction: "outgoing", "incoming", or "both"
		    max_depth: Maximum traversal depth (default 1)

		Returns:
		    List of neighbor entities with relationship info
		"""
		neighbors = []
		visited = {entity_name}
		queue = deque([(entity_name, 0)])  # (entity, depth)

		while queue:
			current, depth = queue.popleft()

			if depth >= max_depth:
				continue

			# Get outgoing relationships
			if direction in ("outgoing", "both"):
				outgoing = self._get_outgoing_relationships(current, relationship_types)
				for rel in outgoing:
					if rel.target_entity not in visited:
						visited.add(rel.target_entity)
						neighbors.append(
							{
								"entity": rel.target_entity,
								"relationship": rel.name,
								"relationship_type": rel.relationship_type,
								"direction": "outgoing",
								"depth": depth + 1,
							}
						)
						if depth + 1 < max_depth:
							queue.append((rel.target_entity, depth + 1))

			# Get incoming relationships
			if direction in ("incoming", "both"):
				incoming = self._get_incoming_relationships(current, relationship_types)
				for rel in incoming:
					if rel.source_entity not in visited:
						visited.add(rel.source_entity)
						neighbors.append(
							{
								"entity": rel.source_entity,
								"relationship": rel.name,
								"relationship_type": rel.relationship_type,
								"direction": "incoming",
								"depth": depth + 1,
							}
						)
						if depth + 1 < max_depth:
							queue.append((rel.source_entity, depth + 1))

		return neighbors

	def _get_outgoing_relationships(self, entity_name, relationship_types=None):
		"""Get outgoing relationships from an entity."""
		filters = {"source_entity": entity_name, "is_active": 1}

		if relationship_types:
			filters["relationship_type"] = ["in", relationship_types]

		return frappe.get_all(
			"Compliance Graph Relationship",
			filters=filters,
			fields=["name", "relationship_type", "target_entity", "weight"],
		)

	def _get_incoming_relationships(self, entity_name, relationship_types=None):
		"""Get incoming relationships to an entity."""
		filters = {"target_entity": entity_name, "is_active": 1}

		if relationship_types:
			filters["relationship_type"] = ["in", relationship_types]

		return frappe.get_all(
			"Compliance Graph Relationship",
			filters=filters,
			fields=["name", "relationship_type", "source_entity", "weight"],
		)

	def find_path(self, start_entity, end_entity, relationship_types=None, max_depth=5):
		"""
		Find shortest path between two entities using BFS.

		Args:
		    start_entity: Starting entity name
		    end_entity: Target entity name
		    relationship_types: Optional list of relationship types to traverse
		    max_depth: Maximum search depth

		Returns:
		    Dict with path entities and relationships, or None if no path found
		"""
		if start_entity == end_entity:
			return {"entities": [start_entity], "relationships": [], "length": 0}

		# BFS for shortest path
		visited = {start_entity}
		queue = deque([(start_entity, [start_entity], [])])

		while queue:
			current, path_entities, path_relationships = queue.popleft()

			if len(path_entities) > max_depth:
				continue

			# Check all neighbors
			neighbors = self.get_neighbors(
				current, relationship_types=relationship_types, direction="both", max_depth=1
			)

			for neighbor in neighbors:
				neighbor_entity = neighbor["entity"]

				if neighbor_entity == end_entity:
					return {
						"entities": path_entities + [end_entity],
						"relationships": path_relationships + [neighbor["relationship"]],
						"length": len(path_entities),
					}

				if neighbor_entity not in visited:
					visited.add(neighbor_entity)
					queue.append(
						(
							neighbor_entity,
							path_entities + [neighbor_entity],
							path_relationships + [neighbor["relationship"]],
						)
					)

		return None  # No path found

	def find_all_paths(self, start_entity, end_entity, relationship_types=None, max_depth=5, max_paths=10):
		"""
		Find all paths between two entities (up to max_paths).

		Args:
		    start_entity: Starting entity name
		    end_entity: Target entity name
		    relationship_types: Optional list of relationship types
		    max_depth: Maximum path length
		    max_paths: Maximum number of paths to return

		Returns:
		    List of path dicts
		"""
		all_paths = []

		def dfs(current, path_entities, path_relationships, visited):
			if len(all_paths) >= max_paths:
				return

			if current == end_entity:
				all_paths.append(
					{
						"entities": path_entities.copy(),
						"relationships": path_relationships.copy(),
						"length": len(path_entities) - 1,
					}
				)
				return

			if len(path_entities) > max_depth:
				return

			neighbors = self.get_neighbors(
				current, relationship_types=relationship_types, direction="both", max_depth=1
			)

			for neighbor in neighbors:
				neighbor_entity = neighbor["entity"]
				if neighbor_entity not in visited:
					visited.add(neighbor_entity)
					path_entities.append(neighbor_entity)
					path_relationships.append(neighbor["relationship"])

					dfs(neighbor_entity, path_entities, path_relationships, visited)

					path_entities.pop()
					path_relationships.pop()
					visited.remove(neighbor_entity)

		dfs(start_entity, [start_entity], [], {start_entity})
		return all_paths

	def traverse(
		self,
		start_entity,
		relationship_types=None,
		entity_types=None,
		direction="outgoing",
		max_depth=3,
		include_start=True,
	):
		"""
		Traverse the graph from a starting entity.

		Args:
		    start_entity: Starting entity name
		    relationship_types: Optional list of relationship types to follow
		    entity_types: Optional list of entity types to include in results
		    direction: "outgoing", "incoming", or "both"
		    max_depth: Maximum traversal depth
		    include_start: Whether to include starting entity in results

		Returns:
		    Dict with entities and relationships found
		"""
		entities = {}
		relationships = []
		visited = set()

		if include_start:
			entity = self.get_entity(start_entity)
			if entity:
				entities[start_entity] = entity

		queue = deque([(start_entity, 0)])
		visited.add(start_entity)

		while queue:
			current, depth = queue.popleft()

			if depth >= max_depth:
				continue

			neighbors = self.get_neighbors(
				current, relationship_types=relationship_types, direction=direction, max_depth=1
			)

			for neighbor in neighbors:
				neighbor_name = neighbor["entity"]
				entity = self.get_entity(neighbor_name)

				if not entity:
					continue

				# Filter by entity type if specified
				if entity_types and entity.get("entity_type") not in entity_types:
					continue

				# Add relationship
				rel_data = {
					"name": neighbor["relationship"],
					"type": neighbor["relationship_type"],
					"source": current if neighbor["direction"] == "outgoing" else neighbor_name,
					"target": neighbor_name if neighbor["direction"] == "outgoing" else current,
				}
				relationships.append(rel_data)

				# Add entity and continue traversal
				if neighbor_name not in visited:
					visited.add(neighbor_name)
					entities[neighbor_name] = entity
					queue.append((neighbor_name, depth + 1))

		return {"entities": list(entities.values()), "relationships": relationships, "count": len(entities)}

	def get_subgraph(self, entity_names):
		"""
		Get a subgraph containing specified entities and their inter-relationships.

		Args:
		    entity_names: List of entity names to include

		Returns:
		    Dict with entities and relationships
		"""
		entities = []
		relationships = []
		entity_set = set(entity_names)

		# Get all entities
		for name in entity_names:
			entity = self.get_entity(name)
			if entity:
				entities.append(entity)

		# Get relationships between these entities
		for name in entity_names:
			outgoing = self._get_outgoing_relationships(name)
			for rel in outgoing:
				if rel.target_entity in entity_set:
					relationships.append(
						{
							"name": rel.name,
							"type": rel.relationship_type,
							"source": name,
							"target": rel.target_entity,
							"weight": rel.weight,
						}
					)

		return {"entities": entities, "relationships": relationships}

	def get_entities_by_type(self, entity_type, filters=None, limit=100):
		"""
		Get all entities of a specific type.

		Args:
		    entity_type: The entity type
		    filters: Additional filters dict
		    limit: Maximum entities to return

		Returns:
		    List of entity dicts
		"""
		query_filters = {"entity_type": entity_type, "is_active": 1}

		if filters:
			query_filters.update(filters)

		entities = frappe.get_all(
			"Compliance Graph Entity",
			filters=query_filters,
			fields=[
				"name",
				"entity_type",
				"entity_doctype",
				"entity_id",
				"entity_label",
				"properties",
				"node_color",
				"node_size",
			],
			limit=limit,
		)

		return entities

	def get_relationship_count(self, entity_name):
		"""
		Get count of relationships for an entity.

		Args:
		    entity_name: The entity name

		Returns:
		    Dict with incoming and outgoing counts
		"""
		outgoing = frappe.db.count(
			"Compliance Graph Relationship", {"source_entity": entity_name, "is_active": 1}
		)

		incoming = frappe.db.count(
			"Compliance Graph Relationship", {"target_entity": entity_name, "is_active": 1}
		)

		return {"outgoing": outgoing, "incoming": incoming, "total": outgoing + incoming}

	def get_graph_for_visualization(
		self, entity_type=None, relationship_types=None, center_entity=None, max_nodes=100, depth=2
	):
		"""
		Get graph data formatted for vis.js visualization.

		Args:
		    entity_type: Optional filter by entity type
		    relationship_types: Optional filter by relationship types
		    center_entity: Optional center entity for ego graph
		    max_nodes: Maximum nodes to return
		    depth: Depth for ego graph (when center_entity specified)

		Returns:
		    Dict with nodes and edges for vis.js
		"""
		nodes = []
		edges = []
		entity_map = {}

		if center_entity:
			# Ego graph centered on entity
			traversal = self.traverse(
				center_entity, relationship_types=relationship_types, max_depth=depth, include_start=True
			)

			# Bulk load entity data to avoid N+1 queries
			entity_names = [e["name"] for e in traversal["entities"]]
			if entity_names:
				entities_data = frappe.get_all(
					"Compliance Graph Entity",
					filters={"name": ["in", entity_names]},
					fields=[
						"name",
						"entity_label",
						"entity_id",
						"entity_type",
						"node_color",
						"node_size",
						"entity_doctype",
					],
				)
				for entity in entities_data:
					nodes.append(
						{
							"id": entity.name,
							"label": entity.entity_label or entity.entity_id,
							"title": f"{entity.entity_type}: {entity.entity_label}",
							"group": entity.entity_type,
							"color": entity.node_color,
							"size": entity.node_size,
							"entity_type": entity.entity_type,
							"entity_doctype": entity.entity_doctype,
							"entity_id": entity.entity_id,
						}
					)
					entity_map[entity.name] = True

			# Bulk load relationship data to avoid N+1 queries
			rel_names = [
				r["name"]
				for r in traversal["relationships"]
				if r["source"] in entity_map and r["target"] in entity_map
			]
			if rel_names:
				rels_data = frappe.get_all(
					"Compliance Graph Relationship",
					filters={"name": ["in", rel_names]},
					fields=["name", "source_entity", "target_entity", "relationship_type", "weight"],
				)
				for rel in rels_data:
					edges.append(
						{
							"id": rel.name,
							"from": rel.source_entity,
							"to": rel.target_entity,
							"label": rel.relationship_type,
							"arrows": "to",
							"color": "#7f8c8d",
							"width": max(1, int(rel.weight * 3)) if rel.weight else 2,
						}
					)

		else:
			# Get entities with optional filter
			filters = {"is_active": 1}
			if entity_type:
				filters["entity_type"] = entity_type

			# Load all needed fields to avoid N+1 queries
			entities = frappe.get_all(
				"Compliance Graph Entity",
				filters=filters,
				fields=[
					"name",
					"entity_label",
					"entity_id",
					"entity_type",
					"node_color",
					"node_size",
					"entity_doctype",
				],
				limit=max_nodes,
			)

			for entity in entities:
				nodes.append(
					{
						"id": entity.name,
						"label": entity.entity_label or entity.entity_id,
						"title": f"{entity.entity_type}: {entity.entity_label}",
						"group": entity.entity_type,
						"color": entity.node_color,
						"size": entity.node_size,
						"entity_type": entity.entity_type,
						"entity_doctype": entity.entity_doctype,
						"entity_id": entity.entity_id,
					}
				)
				entity_map[entity.name] = True

			# Get relationships
			rel_filters = {"is_active": 1}
			if relationship_types:
				rel_filters["relationship_type"] = ["in", relationship_types]

			relationships = frappe.get_all(
				"Compliance Graph Relationship",
				filters=rel_filters,
				fields=["name", "source_entity", "target_entity"],
			)

			for rel in relationships:
				if rel.source_entity in entity_map and rel.target_entity in entity_map:
					rel_doc = frappe.get_doc("Compliance Graph Relationship", rel.name)
					edges.append(rel_doc.to_vis_edge())

		return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}

	def pattern_match(self, pattern):
		"""
		Find subgraphs matching a pattern.

		Pattern format:
		{
		    "nodes": [
		        {"var": "c", "type": "Control"},
		        {"var": "r", "type": "Risk"}
		    ],
		    "edges": [
		        {"from": "c", "to": "r", "type": "MITIGATES"}
		    ]
		}

		Args:
		    pattern: Pattern specification dict

		Returns:
		    List of matching subgraphs
		"""
		matches = []
		nodes = pattern.get("nodes", [])
		edges = pattern.get("edges", [])

		if not nodes:
			return matches

		# Get candidates for first node
		first_node = nodes[0]
		candidates = self.get_entities_by_type(first_node["type"])

		for candidate in candidates:
			# Try to match from this candidate
			bindings = {first_node["var"]: candidate["name"]}
			match = self._try_pattern_match(nodes[1:], edges, bindings)

			if match:
				matches.append(match)

		return matches

	def _try_pattern_match(self, remaining_nodes, edges, bindings):
		"""Try to complete pattern match with current bindings."""
		if not remaining_nodes:
			# Check all edges are satisfied
			for edge in edges:
				from_entity = bindings.get(edge["from"])
				to_entity = bindings.get(edge["to"])

				if not from_entity or not to_entity:
					return None

				# Check relationship exists
				exists = frappe.db.exists(
					"Compliance Graph Relationship",
					{
						"source_entity": from_entity,
						"target_entity": to_entity,
						"relationship_type": edge["type"],
						"is_active": 1,
					},
				)

				if not exists:
					return None

			return bindings.copy()

		# Try to bind next node
		next_node = remaining_nodes[0]
		candidates = self.get_entities_by_type(next_node["type"])

		for candidate in candidates:
			if candidate["name"] in bindings.values():
				continue  # Already bound

			new_bindings = bindings.copy()
			new_bindings[next_node["var"]] = candidate["name"]

			result = self._try_pattern_match(remaining_nodes[1:], edges, new_bindings)
			if result:
				return result

		return None


# API Endpoints
@frappe.whitelist()
def get_entity_neighbors(entity_name, relationship_types=None, direction="both", max_depth=1):
	"""
	API endpoint to get entity neighbors.

	Args:
	    entity_name: Entity to query
	    relationship_types: Comma-separated list of relationship types
	    direction: "outgoing", "incoming", or "both"
	    max_depth: Maximum depth
	"""
	if not frappe.has_permission("Compliance Graph Entity", "read"):
		frappe.throw(_("No permission to read graph entities"))

	engine = GraphQueryEngine()

	rel_types = None
	if relationship_types:
		rel_types = [r.strip() for r in relationship_types.split(",")]

	return engine.get_neighbors(
		entity_name, relationship_types=rel_types, direction=direction, max_depth=cint(max_depth)
	)


@frappe.whitelist()
def find_entity_path(start_entity, end_entity, relationship_types=None, max_depth=5):
	"""
	API endpoint to find path between entities.

	Args:
	    start_entity: Starting entity
	    end_entity: Target entity
	    relationship_types: Comma-separated list of relationship types
	    max_depth: Maximum path length
	"""
	if not frappe.has_permission("Compliance Graph Entity", "read"):
		frappe.throw(_("No permission to read graph entities"))

	engine = GraphQueryEngine()

	rel_types = None
	if relationship_types:
		rel_types = [r.strip() for r in relationship_types.split(",")]

	return engine.find_path(start_entity, end_entity, relationship_types=rel_types, max_depth=cint(max_depth))


@frappe.whitelist()
def get_visualization_data(entity_type=None, center_entity=None, depth=2, max_nodes=100):
	"""
	API endpoint to get graph visualization data.

	Args:
	    entity_type: Optional filter by entity type
	    center_entity: Optional center entity for ego graph
	    depth: Traversal depth
	    max_nodes: Maximum nodes to return
	"""
	if not frappe.has_permission("Compliance Graph Entity", "read"):
		frappe.throw(_("No permission to read graph entities"))

	engine = GraphQueryEngine()

	return engine.get_graph_for_visualization(
		entity_type=entity_type, center_entity=center_entity, depth=cint(depth), max_nodes=cint(max_nodes)
	)


@frappe.whitelist()
def get_graph_statistics():
	"""Get overall graph statistics."""
	if not frappe.has_permission("Compliance Graph Entity", "read"):
		frappe.throw(_("No permission to read graph entities"))

	stats = {
		"total_entities": frappe.db.count("Compliance Graph Entity", {"is_active": 1}),
		"total_relationships": frappe.db.count("Compliance Graph Relationship", {"is_active": 1}),
		"total_paths": frappe.db.count("Compliance Graph Path", {"is_valid": 1}),
		"entities_by_type": {},
		"relationships_by_type": {},
	}

	# Count by entity type
	entity_counts = frappe.db.sql(
		"""
        SELECT entity_type, COUNT(*) as count
        FROM `tabCompliance Graph Entity`
        WHERE is_active = 1
        GROUP BY entity_type
    """,
		as_dict=True,
	)

	for row in entity_counts:
		stats["entities_by_type"][row.entity_type] = row.count

	# Count by relationship type
	rel_counts = frappe.db.sql(
		"""
        SELECT relationship_type, COUNT(*) as count
        FROM `tabCompliance Graph Relationship`
        WHERE is_active = 1
        GROUP BY relationship_type
    """,
		as_dict=True,
	)

	for row in rel_counts:
		stats["relationships_by_type"][row.relationship_type] = row.count

	return stats
