"""
test_generate_graph.py — Unit tests for the SignalAgent synthetic data generator.

Run with:
    pytest test_generate_graph.py -v

The fixture generates a small graph (200 persons / 50 companies / 50 posts /
10 signal sources) once per module so the full suite completes in seconds.
"""

import csv
import importlib.util
import pickle
from pathlib import Path
from typing import Dict, List

import networkx as nx
import numpy as np
import pytest

from generate_graph import generate_graph

# ─────────────────────────────────────────────────────────────────────────────
# SMALL-GRAPH PARAMETERS  (fast enough to run in CI)
# ─────────────────────────────────────────────────────────────────────────────
N_PERSONS = 200
N_COMPANIES = 50
N_POSTS = 50
N_SIGNAL_SOURCES = 10
N_COMMUNITIES = 3
QUALIFIED_FRACTION = 0.28
HOMOPHILY_ALPHA = 0.70
SEED = 42


# ─────────────────────────────────────────────────────────────────────────────
# MODULE-SCOPED FIXTURE  (generated once, reused by every test)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    """Generate a small graph once and share it across all tests."""
    out_dir = tmp_path_factory.mktemp("graph_output")
    G, graph_path, labels_path = generate_graph(
        n_persons=N_PERSONS,
        n_companies=N_COMPANIES,
        n_posts=N_POSTS,
        n_signal_sources=N_SIGNAL_SOURCES,
        n_communities=N_COMMUNITIES,
        qualified_fraction=QUALIFIED_FRACTION,
        homophily_alpha=HOMOPHILY_ALPHA,
        seed=SEED,
        llm_profiles=False,
        out_dir=str(out_dir),
        verbose=False,
    )
    return G, graph_path, labels_path


@pytest.fixture(scope="module")
def labels(generated):
    """Parse labels.csv into a dict {person_id: bool}."""
    _, _, labels_path = generated
    result: Dict[str, bool] = {}
    with open(labels_path) as f:
        for row in csv.DictReader(f):
            result[row["person_id"]] = row["qualified"].strip().lower() in ("true", "1")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────────────────────

def edges_of_type(G: nx.MultiDiGraph, edge_type: str):
    return [
        (u, v, d)
        for u, v, _, d in G.edges(data=True, keys=True)
        if d.get("edge_type") == edge_type
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 1. NODE COUNTS
# ─────────────────────────────────────────────────────────────────────────────

class TestNodeCounts:
    def test_person_count(self, generated):
        G, _, _ = generated
        persons = [n for n, d in G.nodes(data=True) if d["node_type"] == "person"]
        assert len(persons) == N_PERSONS, (
            f"Expected {N_PERSONS} Person nodes, got {len(persons)}"
        )

    def test_company_count(self, generated):
        G, _, _ = generated
        companies = [n for n, d in G.nodes(data=True) if d["node_type"] == "company"]
        assert len(companies) == N_COMPANIES, (
            f"Expected {N_COMPANIES} Company nodes, got {len(companies)}"
        )

    def test_post_count(self, generated):
        G, _, _ = generated
        posts = [n for n, d in G.nodes(data=True) if d["node_type"] == "post"]
        assert len(posts) == N_POSTS, (
            f"Expected {N_POSTS} Post nodes, got {len(posts)}"
        )

    def test_signal_source_count(self, generated):
        G, _, _ = generated
        sources = [n for n, d in G.nodes(data=True) if d["node_type"] == "signal_source"]
        assert len(sources) == N_SIGNAL_SOURCES, (
            f"Expected {N_SIGNAL_SOURCES} SignalSource nodes, got {len(sources)}"
        )

    def test_total_node_count(self, generated):
        G, _, _ = generated
        expected = N_PERSONS + N_COMPANIES + N_POSTS + N_SIGNAL_SOURCES
        assert G.number_of_nodes() == expected, (
            f"Expected {expected} total nodes, got {G.number_of_nodes()}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. EDGE COUNTS & TOPOLOGY
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCounts:
    def test_engaged_with_edges_exist(self, generated):
        G, _, _ = generated
        edges = edges_of_type(G, "engaged_with")
        assert len(edges) > 0, "No engaged_with edges found"

    def test_engaged_with_minimum_volume(self, generated):
        G, _, _ = generated
        edges = edges_of_type(G, "engaged_with")
        # Every person gets at least 1 engagement (degree capped at 1 minimum in Zipf)
        assert len(edges) >= N_PERSONS, (
            f"Expected ≥{N_PERSONS} engaged_with edges (1 per person min), "
            f"got {len(edges)}"
        )

    def test_engaged_with_subtypes_valid(self, generated):
        G, _, _ = generated
        valid = {"like", "comment", "reshare"}
        for u, v, d in edges_of_type(G, "engaged_with"):
            assert d.get("subtype") in valid, (
                f"Invalid engaged_with subtype: {d.get('subtype')!r}"
            )

    def test_engaged_with_topology(self, generated):
        G, _, _ = generated
        for u, v, d in edges_of_type(G, "engaged_with"):
            assert G.nodes[u]["node_type"] == "person", (
                f"engaged_with source {u} is not a person"
            )
            assert G.nodes[v]["node_type"] == "post", (
                f"engaged_with target {v} is not a post"
            )

    def test_works_at_count(self, generated):
        G, _, _ = generated
        edges = edges_of_type(G, "works_at")
        assert len(edges) == N_PERSONS, (
            f"Expected exactly {N_PERSONS} works_at edges (one per person), "
            f"got {len(edges)}"
        )

    def test_works_at_topology(self, generated):
        G, _, _ = generated
        for u, v, d in edges_of_type(G, "works_at"):
            assert G.nodes[u]["node_type"] == "person"
            assert G.nodes[v]["node_type"] == "company"

    def test_belongs_to_count(self, generated):
        G, _, _ = generated
        edges = edges_of_type(G, "belongs_to")
        assert len(edges) == N_POSTS, (
            f"Expected {N_POSTS} belongs_to edges (one per post), got {len(edges)}"
        )

    def test_belongs_to_topology(self, generated):
        G, _, _ = generated
        for u, v, d in edges_of_type(G, "belongs_to"):
            assert G.nodes[u]["node_type"] == "post"
            assert G.nodes[v]["node_type"] == "signal_source"

    def test_authored_edges_exist(self, generated):
        G, _, _ = generated
        edges = edges_of_type(G, "authored")
        assert len(edges) > 0, "No authored edges found"

    def test_authored_topology(self, generated):
        G, _, _ = generated
        for u, v, d in edges_of_type(G, "authored"):
            assert G.nodes[u]["node_type"] == "person"
            assert G.nodes[v]["node_type"] == "post"

    def test_total_edge_count_reasonable(self, generated):
        G, _, _ = generated
        # Minimum: works_at + belongs_to + at least 1 engagement per person
        min_edges = N_PERSONS + N_POSTS + N_PERSONS
        assert G.number_of_edges() >= min_edges, (
            f"Expected ≥{min_edges} total edges, got {G.number_of_edges()}"
        )

    def test_engaged_with_has_timestamps(self, generated):
        G, _, _ = generated
        for u, v, d in edges_of_type(G, "engaged_with"):
            assert "timestamp" in d, f"engaged_with edge ({u}→{v}) missing timestamp"
            break  # spot-check first edge


# ─────────────────────────────────────────────────────────────────────────────
# 3. QUALIFIED LABELS
# ─────────────────────────────────────────────────────────────────────────────

class TestQualifiedLabels:
    def test_at_least_20_percent_qualified(self, labels):
        q = sum(v for v in labels.values())
        total = len(labels)
        frac = q / total
        assert frac >= 0.20, (
            f"Expected ≥20% qualified persons, got {frac:.1%} ({q}/{total})"
        )

    def test_labels_csv_columns(self, generated):
        _, _, labels_path = generated
        with open(labels_path) as f:
            reader = csv.DictReader(f)
            assert "person_id" in reader.fieldnames, "Missing column: person_id"
            assert "qualified" in reader.fieldnames, "Missing column: qualified"

    def test_labels_csv_row_count(self, labels):
        assert len(labels) == N_PERSONS, (
            f"Expected {N_PERSONS} rows in labels.csv, got {len(labels)}"
        )

    def test_labels_person_ids_match_graph(self, generated, labels):
        G, _, _ = generated
        graph_person_ids = {
            n for n, d in G.nodes(data=True) if d["node_type"] == "person"
        }
        assert set(labels.keys()) == graph_person_ids, (
            "Person IDs in labels.csv do not match Person nodes in graph"
        )

    def test_labels_consistent_with_graph_attribute(self, generated, labels):
        G, _, _ = generated
        mismatches = []
        for pid, csv_label in labels.items():
            graph_label = G.nodes[pid].get("qualified")
            if graph_label != csv_label:
                mismatches.append(
                    f"{pid}: graph={graph_label!r}, csv={csv_label!r}"
                )
        assert not mismatches, (
            f"qualified attribute mismatch for {len(mismatches)} persons:\n"
            + "\n".join(mismatches[:5])
        )

    def test_both_classes_present(self, labels):
        values = set(labels.values())
        assert True in values, "No qualified=True persons found"
        assert False in values, "No qualified=False persons found"


# ─────────────────────────────────────────────────────────────────────────────
# 4. STRUCTURAL PROPERTIES
# ─────────────────────────────────────────────────────────────────────────────

class TestStructuralProperties:
    def test_graph_is_multidigraph(self, generated):
        G, _, _ = generated
        assert isinstance(G, nx.MultiDiGraph), (
            f"Expected nx.MultiDiGraph, got {type(G).__name__}"
        )

    def test_graph_pkl_roundtrip(self, generated):
        G, graph_path, _ = generated
        with open(graph_path, "rb") as f:
            G2 = pickle.load(f)
        assert G2.number_of_nodes() == G.number_of_nodes()
        assert G2.number_of_edges() == G.number_of_edges()

    def test_power_law_engagement_skew(self, generated):
        """
        Engagement degrees should follow a right-skewed power-law distribution.
        We measure this with the Gini coefficient: for a Zipf distribution with
        a≈2.2 on a graph of this size, Gini should comfortably exceed 0.40.
        """
        G, _, _ = generated
        degrees = np.array([
            sum(
                1 for _, _, d in G.out_edges(n, data=True)
                if d.get("edge_type") == "engaged_with"
            )
            for n, attrs in G.nodes(data=True)
            if attrs["node_type"] == "person"
        ], dtype=float)

        sorted_d = np.sort(degrees)
        n = len(sorted_d)
        if sorted_d.sum() == 0:
            pytest.skip("All degrees are 0; cannot compute Gini")

        gini = (
            2.0 * np.dot(np.arange(1, n + 1), sorted_d) / (n * sorted_d.sum())
        ) - (n + 1) / n

        assert gini > 0.40, (
            f"Expected right-skewed degree distribution (Gini > 0.40), got {gini:.3f}"
        )

    def test_homophily_qualified_prefer_magnet_posts(self, generated):
        """
        Qualified persons should engage with magnet posts at a higher rate
        than unqualified persons (the homophily property).
        """
        G, _, _ = generated
        magnet_posts = {
            n for n, d in G.nodes(data=True)
            if d["node_type"] == "post" and d.get("is_magnet", False)
        }
        if not magnet_posts:
            pytest.skip("No magnet posts generated")

        qual_total = qual_magnet = 0
        unqual_total = unqual_magnet = 0

        for u, v, d in edges_of_type(G, "engaged_with"):
            is_q = G.nodes[u].get("qualified", False)
            is_m = v in magnet_posts
            if is_q:
                qual_total += 1
                qual_magnet += int(is_m)
            else:
                unqual_total += 1
                unqual_magnet += int(is_m)

        if qual_total == 0 or unqual_total == 0:
            pytest.skip("Insufficient engagement data for homophily test")

        qual_rate = qual_magnet / qual_total
        unqual_rate = unqual_magnet / unqual_total
        assert qual_rate > unqual_rate, (
            f"Homophily not detected: qualified magnet rate {qual_rate:.3f} "
            f"≤ unqualified rate {unqual_rate:.3f}"
        )

    def test_person_required_attributes(self, generated):
        G, _, _ = generated
        required = {
            "node_type", "name", "role", "seniority", "company_id",
            "region", "community_id", "profile_text", "qualified",
        }
        for n, d in G.nodes(data=True):
            if d["node_type"] == "person":
                missing = required - set(d.keys())
                assert not missing, f"Person {n} missing attributes: {missing}"

    def test_post_required_attributes(self, generated):
        G, _, _ = generated
        required = {"node_type", "topic", "signal_source_id", "is_magnet", "engagement_count"}
        for n, d in G.nodes(data=True):
            if d["node_type"] == "post":
                missing = required - set(d.keys())
                assert not missing, f"Post {n} missing attributes: {missing}"

    def test_engagement_counts_reflect_edges(self, generated):
        """
        The engagement_count attribute on Post nodes should match the number
        of incoming engaged_with edges on that post.
        """
        G, _, _ = generated
        # Count actual incoming engaged_with edges per post
        actual_counts: Dict[str, int] = {}
        for u, v, d in edges_of_type(G, "engaged_with"):
            actual_counts[v] = actual_counts.get(v, 0) + 1

        mismatches = []
        for n, d in G.nodes(data=True):
            if d["node_type"] == "post":
                expected = actual_counts.get(n, 0)
                stored = d.get("engagement_count", -1)
                if stored != expected:
                    mismatches.append(
                        f"{n}: stored={stored}, actual={expected}"
                    )
        assert not mismatches, (
            f"engagement_count mismatch on {len(mismatches)} posts:\n"
            + "\n".join(mismatches[:5])
        )

    def test_community_ids_are_valid(self, generated):
        G, _, _ = generated
        valid_ids = set(range(N_COMMUNITIES))
        for n, d in G.nodes(data=True):
            if d["node_type"] in ("person", "post", "company"):
                assert d.get("community_id") in valid_ids, (
                    f"Node {n} has invalid community_id: {d.get('community_id')!r}"
                )

    def test_all_persons_have_a_company(self, generated):
        G, _, _ = generated
        company_ids = {n for n, d in G.nodes(data=True) if d["node_type"] == "company"}
        for n, d in G.nodes(data=True):
            if d["node_type"] == "person":
                assert d.get("company_id") in company_ids, (
                    f"Person {n} references unknown company: {d.get('company_id')!r}"
                )

    def test_all_posts_have_a_signal_source(self, generated):
        G, _, _ = generated
        ss_ids = {n for n, d in G.nodes(data=True) if d["node_type"] == "signal_source"}
        for n, d in G.nodes(data=True):
            if d["node_type"] == "post":
                assert d.get("signal_source_id") in ss_ids, (
                    f"Post {n} references unknown signal source: "
                    f"{d.get('signal_source_id')!r}"
                )


# ─────────────────────────────────────────────────────────────────────────────
# 5. REPRODUCIBILITY
# ─────────────────────────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_graph(self, tmp_path):
        kwargs = dict(
            n_persons=50, n_companies=10, n_posts=10, n_signal_sources=5,
            seed=SEED, verbose=False, out_dir=str(tmp_path / "run_a"),
        )
        G1, _, _ = generate_graph(**kwargs)
        kwargs["out_dir"] = str(tmp_path / "run_b")
        G2, _, _ = generate_graph(**kwargs)

        assert G1.number_of_nodes() == G2.number_of_nodes()
        assert G1.number_of_edges() == G2.number_of_edges()

        # Spot-check person_0 attributes
        for attr in ("role", "seniority", "community_id", "qualified"):
            assert G1.nodes["person_0"][attr] == G2.nodes["person_0"][attr], (
                f"Attribute '{attr}' of person_0 differs between runs"
            )

    def test_different_seed_different_graph(self, tmp_path):
        base_kwargs = dict(
            n_persons=50, n_companies=10, n_posts=10, n_signal_sources=5,
            verbose=False,
        )
        G1, _, _ = generate_graph(seed=1, out_dir=str(tmp_path / "s1"), **base_kwargs)
        G2, _, _ = generate_graph(seed=2, out_dir=str(tmp_path / "s2"), **base_kwargs)
        # Very unlikely to produce identical edge counts with different seeds
        # (not strictly guaranteed, but practically always true)
        assert G1.number_of_edges() != G2.number_of_edges() or \
               G1.nodes["person_0"]["role"] != G2.nodes["person_0"]["role"], (
            "Different seeds produced identical graphs — check RNG seeding"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. COMMUNITY DETECTION (optional — requires python-louvain)
# ─────────────────────────────────────────────────────────────────────────────

HAS_LOUVAIN = importlib.util.find_spec("community") is not None


@pytest.mark.skipif(not HAS_LOUVAIN, reason="python-louvain not installed")
class TestCommunityDetection:
    def _build_coengagement_graph(self, G: nx.MultiDiGraph) -> nx.Graph:
        """
        Project engaged_with edges onto a person–person co-engagement graph.
        Edge weight = number of posts two persons co-engaged with.
        """
        post_to_persons: Dict[str, List[str]] = {}
        for u, v, d in edges_of_type(G, "engaged_with"):
            post_to_persons.setdefault(v, []).append(u)

        coeng = nx.Graph()
        person_ids = [
            n for n, d in G.nodes(data=True) if d["node_type"] == "person"
        ]
        coeng.add_nodes_from(person_ids)

        for _, persons in post_to_persons.items():
            for i in range(len(persons)):
                for j in range(i + 1, len(persons)):
                    u, v = persons[i], persons[j]
                    if coeng.has_edge(u, v):
                        coeng[u][v]["weight"] += 1
                    else:
                        coeng.add_edge(u, v, weight=1)
        return coeng

    def test_louvain_finds_multiple_communities(self, generated):
        """
        Louvain applied to the person–person co-engagement projection should
        detect at least 2 communities (we planted 3).
        """
        import community as community_louvain

        G, _, _ = generated
        coeng = self._build_coengagement_graph(G)

        if coeng.number_of_edges() == 0:
            pytest.skip("Co-engagement graph has no edges; cannot run Louvain")

        partition = community_louvain.best_partition(coeng)
        n_detected = len(set(partition.values()))
        assert n_detected >= 2, (
            f"Expected ≥2 Louvain communities on planted-community graph, "
            f"found {n_detected}"
        )

    def test_planted_community_labels_align_with_louvain(self, generated):
        """
        Planted community_id labels on Person nodes should show significant
        overlap with Louvain-detected communities (measured via majority vote).
        """
        import community as community_louvain
        from collections import Counter

        G, _, _ = generated
        coeng = self._build_coengagement_graph(G)

        if coeng.number_of_edges() == 0:
            pytest.skip("Co-engagement graph has no edges")

        partition = community_louvain.best_partition(coeng)

        # For each Louvain community, find the majority planted community_id
        louvain_to_planted: Dict[int, List[int]] = {}
        for pid, louvain_c in partition.items():
            planted_c = G.nodes[pid].get("community_id", -1)
            louvain_to_planted.setdefault(louvain_c, []).append(planted_c)

        # Each Louvain cluster should be dominated by one planted community
        purity_scores = []
        for louvain_c, planted_list in louvain_to_planted.items():
            counter = Counter(planted_list)
            majority_count = counter.most_common(1)[0][1]
            purity_scores.append(majority_count / len(planted_list))

        avg_purity = sum(purity_scores) / len(purity_scores)
        # At small test-graph scale (200 persons) community signal is weaker;
        # threshold is 0.35. At production scale (5K persons) expect > 0.60.
        assert avg_purity > 0.35, (
            f"Louvain cluster purity too low ({avg_purity:.2f}); "
            "planted communities may not be detectable"
        )
