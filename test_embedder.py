import unittest
import os
import tempfile
import numpy as np
from database import init_db
from embedder import (
    compose_top_text,
    compose_bottom_text,
    compose_hair_text,
    compute_garment_similarity,
    compute_hair_similarity,
    compute_person_similarity,
    classical_mds,
    get_cosine_similarity
)

class TestEmbedder(unittest.TestCase):

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        init_db(self.db_path)

    def tearDown(self):
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_text_compositions(self):
        """Verify natural-language description builders compose styling values correctly."""
        # Top
        top = {
            "type": "halter top",
            "color": "red",
            "fit": "fitted",
            "fabric": "satin",
            "pattern": "solid",
            "neckline": "halter",
            "sleeve_length": "sleeveless",
            "details": ["ruched", "spaghetti straps"]
        }
        self.assertEqual(
            compose_top_text(top),
            "red fitted satin halter top with halter neckline, sleeveless, ruched, spaghetti straps"
        )
        self.assertIsNone(compose_top_text({}))

        # Bottom
        bottom = {
            "type": "jeans",
            "color": "black",
            "fit": "slim",
            "fabric": "denim",
            "pattern": "solid",
            "garment_length": "ankle",
            "details": ["distressed"]
        }
        self.assertEqual(
            compose_bottom_text(bottom),
            "black slim denim jeans with ankle length, distressed"
        )
        self.assertIsNone(compose_bottom_text({}))

        # Hair
        hair = {
            "color": "blonde",
            "texture": "wavy",
            "length": "long",
            "style": "down"
        }
        self.assertEqual(compose_hair_text(hair), "blonde wavy long hair worn down")
        self.assertIsNone(compose_hair_text({}))

    def test_garment_similarity_exact_matches(self):
        """Verify compute_garment_similarity produces 1.0 for identical garments."""
        g1 = {
            "type": "hoodie",
            "color": "gray",
            "fit": "oversized",
            "fabric": "cotton",
            "pattern": "solid",
            "details": ["logo"]
        }
        # Exact match (without cached embeddings fallback will use string matching)
        sim = compute_garment_similarity(g1, g1, self.db_path)
        self.assertEqual(sim, 1.0)

    def test_garment_similarity_mismatches(self):
        """Verify attribute mismatch logic produces proportional weight drops."""
        g1 = {
            "type": "t-shirt",
            "color": "white",
            "fit": "fitted",
            "fabric": "cotton",
            "pattern": "solid",
            "details": []
        }
        # Fabric differs (cotton vs linen). Since fabric weight is 0.15:
        # Active weights: type (0.30), color (0.25), fabric (0.15), pattern (0.10), fit (0.08) = 0.88 sum.
        # Expected similarity: (0.88 - 0.15) / 0.88 = 0.73 / 0.88
        g2 = g1.copy()
        g2["fabric"] = "linen"
        
        sim = compute_garment_similarity(g1, g2, self.db_path)
        self.assertAlmostEqual(sim, 0.73 / 0.88, places=4)

    def test_garment_similarity_null_redistribution(self):
        """Verify weight redistribution when some attributes are null on both sides."""
        # Only type and color are set. Fit/Fabric/Pattern/details are null.
        g1 = {
            "type": "jacket",
            "color": "blue",
            "fit": None,
            "fabric": None,
            "pattern": None,
            "details": []
        }
        g2 = {
            "type": "jacket",
            "color": "red",
            "fit": None,
            "fabric": None,
            "pattern": None,
            "details": []
        }
        # Standard weights: type: 0.30, color: 0.25. Sum = 0.55.
        # Since type matches (1.0) and color differs (0.0):
        # sim = (1.0 * 0.30 + 0.0 * 0.25) / 0.55 = 0.30 / 0.55 = 0.54545...
        sim = compute_garment_similarity(g1, g2, self.db_path)
        self.assertAlmostEqual(sim, 0.30 / 0.55, places=4)

    def test_hair_similarity(self):
        """Verify compute_hair_similarity handles text features and weights."""
        h1 = {
            "color": "brunette",
            "length": "short",
            "texture": "straight",
            "style": "ponytail"
        }
        h2 = h1.copy()
        h2["style"] = "down"  # Style differs (weight = 0.15), total should be 0.85
        sim = compute_hair_similarity(h1, h2, self.db_path)
        self.assertAlmostEqual(sim, 0.85, places=4)

    def test_person_similarity_redistributes_components(self):
        """Verify Layer 1 mode and null redistribution is mathematically correct."""
        # Person A: full outfit
        p_a = {
            "hair": {"color": "blonde", "length": "long"},
            "top": {"type": "t-shirt", "color": "white"},
            "bottom": {"type": "jeans", "color": "blue"}
        }
        # Person B: only topwear (bottom is null)
        p_b = {
            "hair": {"color": "blonde", "length": "long"},
            "top": {"type": "t-shirt", "color": "white"},
            "bottom": {"type": None}
        }
        
        # When comparing p_a and p_b:
        # Bottom is null on p_b, so bottom is skipped and its weight (0.35) is redistributed
        # Active components: top, hair. Active weight sum: 0.40 (top) + 0.25 (hair) = 0.65.
        # Sim = (top_sim * 0.40 + hair_sim * 0.25) / 0.65
        # Since top and hair are identical, sim should be 1.0!
        res = compute_person_similarity(p_a, p_b, self.db_path, mode="full")
        self.assertEqual(res["total"], 1.0)
        self.assertEqual(res["top"], 1.0)
        self.assertEqual(res["hair"], 1.0)
        self.assertEqual(res["bottom"], 0.0)

    def test_classical_mds_projection(self):
        """Verify classical_mds outputs correct shape and respects dimensionality."""
        # 3 points with known pairwise distances
        # Point 0 to 1 = 3.0, Point 1 to 2 = 4.0, Point 0 to 2 = 5.0 (Right triangle)
        D = np.array([
            [0.0, 3.0, 5.0],
            [3.0, 0.0, 4.0],
            [5.0, 4.0, 0.0]
        ])
        coords = classical_mds(D, dimensions=2)
        self.assertEqual(coords.shape, (3, 2))
        
        # Verify distance matrix reconstructs similarly
        dist_0_1 = np.linalg.norm(coords[0] - coords[1])
        self.assertAlmostEqual(dist_0_1, 3.0, places=4)

    def test_cosine_similarity_edge_cases(self):
        """Verify cosine similarity behaves correctly with empty/zero vectors."""
        self.assertEqual(get_cosine_similarity([], [1.0, 2.0]), 0.0)
        self.assertEqual(get_cosine_similarity([0.0, 0.0], [1.0, 2.0]), 0.0)
        self.assertAlmostEqual(get_cosine_similarity([1.0, 1.0], [1.0, 1.0]), 1.0)

    def test_garment_similarity_all_null(self):
        """Verify compute_garment_similarity handles entirely empty dictionaries without division errors."""
        sim = compute_garment_similarity({}, {}, self.db_path)
        self.assertEqual(sim, 1.0)

    def test_person_similarity_all_null(self):
        """Verify compute_person_similarity handles entirely empty dictionaries without division errors."""
        res = compute_person_similarity({}, {}, self.db_path, mode="full")
        self.assertEqual(res["total"], 1.0)
        self.assertEqual(res["top"], 0.0)
        self.assertEqual(res["bottom"], 0.0)
        self.assertEqual(res["hair"], 0.0)

if __name__ == "__main__":
    unittest.main()
