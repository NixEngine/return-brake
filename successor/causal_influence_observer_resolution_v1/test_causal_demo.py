"""Tests for the exact causal influence demonstration."""

from __future__ import annotations

import unittest
from pathlib import Path

import causal_demo as demo


class CausalInfluenceDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parent
        cls.specs = demo.world_specs()
        cls.capture_ticks = (
            demo.T0,
            1,
            demo.T1,
            demo.T2,
            demo.T3,
            demo.T3 + 1,
            demo.FUTURE_PROBE,
        )
        cls.simulations = {
            name: demo.simulate(spec, demo.FUTURE_PROBE, cls.capture_ticks)
            for name, spec in cls.specs.items()
        }
        cls.results = demo.build_results()

    def test_w1_and_w0_have_exactly_matched_pre_contact_state(self) -> None:
        self.assertEqual(self.specs["W1"].initial, self.specs["W0"].initial)
        self.assertEqual(self.specs["W0"].suppressions, ((demo.T0, demo.AB_PAIR),))

    def test_standard_tick_is_reversible_on_contact_and_non_contact_samples(self) -> None:
        for sample in demo.roundtrip_samples():
            stepped, _events = demo.standard_step(sample)
            self.assertEqual(demo.reverse_standard_step(stepped), sample)

    def test_event_schedule(self) -> None:
        w1_schedule = [(event["tick"], event["pair"]) for event in self.simulations["W1"].events]
        w0_schedule = [(event["tick"], event["pair"]) for event in self.simulations["W0"].events]
        alt_schedule = [(event["tick"], event["pair"]) for event in self.simulations["W_alt"].events]
        self.assertEqual(w1_schedule, [(demo.T0, ["A", "B"]), (demo.T3, ["B", "C"])])
        self.assertEqual(w0_schedule, [])
        self.assertEqual(alt_schedule, [(demo.T3, ["B", "C"])])

    def test_late_window_is_non_identifying(self) -> None:
        w1_hash = demo.projection_digest(self.specs["W1"], "B", demo.T1, demo.T2)
        w0_hash = demo.projection_digest(self.specs["W0"], "B", demo.T1, demo.T2)
        alt_hash = demo.projection_digest(self.specs["W_alt"], "B", demo.T1, demo.T2)
        self.assertEqual(w1_hash, alt_hash)
        self.assertNotEqual(w1_hash, w0_hash)

        exact_w1_alt = demo.compare_projection_frames(
            self.specs["W1"], self.specs["W_alt"], "B", demo.T1, demo.T2
        )
        exact_w1_w0 = demo.compare_projection_frames(
            self.specs["W1"], self.specs["W0"], "B", demo.T1, demo.T2
        )
        self.assertTrue(exact_w1_alt["equal"])
        self.assertEqual(exact_w1_alt["frames_compared"], 500_001)
        self.assertEqual(exact_w1_alt["mismatch_count"], 0)
        self.assertFalse(exact_w1_w0["equal"])
        self.assertEqual(exact_w1_w0["first_mismatch_tick"], demo.T1)

        ticks = (demo.T1, (demo.T1 + demo.T2) // 2, demo.T2)
        self.assertEqual(
            demo.projection_samples(self.specs["W1"], "B", ticks),
            demo.projection_samples(self.specs["W_alt"], "B", ticks),
        )

    def test_full_history_records_touch_only_in_w1(self) -> None:
        w1_a_b = [
            event
            for event in self.simulations["W1"].events
            if event["tick"] <= demo.T2 and event["pair"] == ["A", "B"]
        ]
        alt_a_b = [
            event
            for event in self.simulations["W_alt"].events
            if event["tick"] <= demo.T2 and event["pair"] == ["A", "B"]
        ]
        self.assertEqual(len(w1_a_b), 1)
        self.assertEqual(w1_a_b[0]["contact_point"], ["0", "0"])
        self.assertEqual(w1_a_b[0]["pre_velocity"]["A"], [1, 1])
        self.assertEqual(w1_a_b[0]["post_velocity"]["B"], [1, -1])
        self.assertEqual(alt_a_b, [])

    def test_matched_counterfactual_effect_reaches_c(self) -> None:
        w1_c = self.simulations["W1"].captures[demo.T3 + 1].body("C")
        w0_c = self.simulations["W0"].captures[demo.T3 + 1].body("C")
        self.assertNotEqual(w1_c, w0_c)
        self.assertEqual(w1_c.vx, 1)
        self.assertEqual(w0_c.vx, 0)

        lineage = demo.lineage_trace(self.simulations["W1"].events)
        self.assertEqual(lineage[0]["vx_lineage_after_contact"]["B"], "A.vx@t0-")
        self.assertEqual(lineage[1]["vx_lineage_after_contact"]["C"], "A.vx@t0-")

    def test_global_counterfactual_states_never_merge_at_reported_ticks(self) -> None:
        for tick in self.capture_ticks[1:]:
            with self.subTest(tick=tick):
                self.assertNotEqual(
                    self.simulations["W1"].captures[tick],
                    self.simulations["W0"].captures[tick],
                )

    def test_per_body_persistence_for_this_trajectory(self) -> None:
        for tick in (1, demo.T1, demo.T2, demo.T3, demo.T3 + 1, demo.FUTURE_PROBE):
            factual = self.simulations["W1"].captures[tick]
            counterfactual = self.simulations["W0"].captures[tick]
            self.assertNotEqual(factual.body("A"), counterfactual.body("A"))
            self.assertNotEqual(factual.body("B"), counterfactual.body("B"))
            if tick >= demo.T3 + 1:
                self.assertNotEqual(factual.body("C"), counterfactual.body("C"))

    def test_generated_artifacts_and_receipt_are_current(self) -> None:
        verification = demo.verify_artifacts(self.root)
        self.assertTrue(verification["passed"], verification)

    def test_results_have_required_claim_boundaries(self) -> None:
        late = self.results["late_observation"]
        self.assertTrue(late["w1_equals_w_alt"])
        self.assertEqual(
            late["exact_frame_comparison"]["W1_vs_W_alt"]["frames_compared"],
            500_001,
        )
        self.assertEqual(
            late["exact_frame_comparison"]["W1_vs_W_alt"]["mismatch_count"],
            0,
        )
        self.assertFalse(late["identifies_a_b_touch_by_itself"])
        self.assertTrue(self.results["full_history_observation"]["identifies_touch_within_model"])
        self.assertTrue(self.results["matched_counterfactual"]["effect_reaches_c"])
        self.assertGreaterEqual(len(self.results["limits"]), 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
