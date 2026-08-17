"""Deterministic causal-persistence and observer-resolution demonstration.

The physical model uses only integer arithmetic and Python's standard library.
See README.md for the proof boundary and interpretation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence


T0 = 0
T1 = 500_000
T2 = 1_000_000
T3 = 1_500_000
FUTURE_PROBE = 1_000_000_000_000

BODY_NAMES = ("A", "B", "C")
BODY_INDEX = {name: index for index, name in enumerate(BODY_NAMES)}
PAIR_ORDER = (("A", "B"), ("A", "C"), ("B", "C"))
AB_PAIR = ("A", "B")

RESULTS_PATH = Path("artifacts/results.json")
CHECKPOINTS_PATH = Path("artifacts/checkpoints.csv")
RECEIPT_PATH = Path("artifacts/SHA256SUMS")
RECEIPT_MEMBERS = (
    Path("README.md"),
    Path("causal_demo.py"),
    Path("test_causal_demo.py"),
    RESULTS_PATH,
    CHECKPOINTS_PATH,
)


@dataclass(frozen=True, slots=True)
class BodyState:
    """One disk's center position and velocity on Z^2."""

    x: int
    y: int
    vx: int
    vy: int

    def advanced(self, ticks: int = 1) -> BodyState:
        return BodyState(
            self.x + ticks * self.vx,
            self.y + ticks * self.vy,
            self.vx,
            self.vy,
        )

    def retreated(self, ticks: int = 1) -> BodyState:
        return self.advanced(-ticks)

    def as_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "vx": self.vx, "vy": self.vy}


@dataclass(frozen=True, slots=True)
class GlobalState:
    """Closed physical state in the fixed A, B, C order."""

    bodies: tuple[BodyState, BodyState, BodyState]

    def body(self, name: str) -> BodyState:
        return self.bodies[BODY_INDEX[name]]

    def replacing(self, name: str, body: BodyState) -> GlobalState:
        items = list(self.bodies)
        items[BODY_INDEX[name]] = body
        return GlobalState(tuple(items))  # type: ignore[arg-type]

    def advanced(self, ticks: int = 1) -> GlobalState:
        return GlobalState(tuple(body.advanced(ticks) for body in self.bodies))  # type: ignore[arg-type]

    def retreated(self, ticks: int = 1) -> GlobalState:
        return GlobalState(tuple(body.retreated(ticks) for body in self.bodies))  # type: ignore[arg-type]

    def as_dict(self) -> dict[str, dict[str, int]]:
        return {name: self.body(name).as_dict() for name in BODY_NAMES}


@dataclass(frozen=True, slots=True)
class WorldSpec:
    """Initial state plus explicitly localized counterfactual suppressions."""

    name: str
    initial: GlobalState
    suppressions: tuple[tuple[int, tuple[str, str]], ...] = ()

    def suppressed_pairs_at(self, tick: int) -> frozenset[tuple[str, str]]:
        return frozenset(pair for event_tick, pair in self.suppressions if event_tick == tick)


@dataclass(frozen=True, slots=True)
class Simulation:
    captures: Mapping[int, GlobalState]
    events: tuple[dict[str, object], ...]


def matched_initial_state() -> GlobalState:
    """The shared W1/W0 state immediately before the t0 contact phase."""

    return GlobalState(
        (
            BodyState(-1, 0, 1, 1),
            BodyState(1, 0, 0, -1),
            BodyState(T3 + 3, -T3, 0, 0),
        )
    )


def world_specs() -> dict[str, WorldSpec]:
    matched = matched_initial_state()
    alternative = GlobalState(
        (
            BodyState(-100, 100, 0, 0),
            BodyState(1, 0, 1, -1),
            BodyState(T3 + 3, -T3, 0, 0),
        )
    )
    return {
        "W1": WorldSpec("W1", matched),
        "W0": WorldSpec("W0", matched, ((T0, AB_PAIR),)),
        "W_alt": WorldSpec("W_alt", alternative),
    }


def is_horizontal_contact(state: GlobalState, pair: tuple[str, str]) -> bool:
    left = state.body(pair[0])
    right = state.body(pair[1])
    return left.y == right.y and abs(right.x - left.x) == 2


def _fraction_text(numerator: int, denominator: int = 2) -> str:
    if numerator % denominator == 0:
        return str(numerator // denominator)
    sign = "-" if numerator < 0 else ""
    return f"{sign}{abs(numerator)}/{denominator}"


def apply_pair_gate(
    state: GlobalState,
    pair: tuple[str, str],
) -> tuple[GlobalState, dict[str, object] | None]:
    """Apply one position-conditioned involutive normal-velocity swap."""

    if not is_horizontal_contact(state, pair):
        return state, None

    left_name, right_name = pair
    left = state.body(left_name)
    right = state.body(right_name)
    approaching = (right.x - left.x) * (right.vx - left.vx) < 0

    new_left = BodyState(left.x, left.y, right.vx, left.vy)
    new_right = BodyState(right.x, right.y, left.vx, right.vy)
    updated = state.replacing(left_name, new_left).replacing(right_name, new_right)

    event: dict[str, object] = {
        "pair": [left_name, right_name],
        "contact_point": [
            _fraction_text(left.x + right.x),
            _fraction_text(left.y + right.y),
        ],
        "normal": [1, 0],
        "approaching_on_realized_trajectory": approaching,
        "rule": "exchange vx; preserve vy",
        "pre_velocity": {
            left_name: [left.vx, left.vy],
            right_name: [right.vx, right.vy],
        },
        "post_velocity": {
            left_name: [new_left.vx, new_left.vy],
            right_name: [new_right.vx, new_right.vy],
        },
    }
    return updated, event


def collision_phase(
    state: GlobalState,
    suppressed_pairs: frozenset[tuple[str, str]] = frozenset(),
) -> tuple[GlobalState, tuple[dict[str, object], ...]]:
    """Apply fixed-order pair gates; each non-suppressed gate is bijective."""

    current = state
    events: list[dict[str, object]] = []
    for pair in PAIR_ORDER:
        if pair in suppressed_pairs:
            continue
        current, event = apply_pair_gate(current, pair)
        if event is not None:
            events.append(event)
    return current, tuple(events)


def standard_step(state: GlobalState) -> tuple[GlobalState, tuple[dict[str, object], ...]]:
    """One ordinary tick: contact phase, then free flight."""

    after_contacts, events = collision_phase(state)
    return after_contacts.advanced(), events


def reverse_standard_step(state: GlobalState) -> GlobalState:
    """Exact inverse of standard_step's state transform."""

    current = state.retreated()
    for pair in reversed(PAIR_ORDER):
        current, _ = apply_pair_gate(current, pair)
    return current


def _integer_solution(a: int, b: int, target: int) -> tuple[str, int | None]:
    """Return ('all', None), ('one', k), or ('none', None) for a + b*k=target."""

    if b == 0:
        return ("all", None) if a == target else ("none", None)
    delta = target - a
    if delta % b:
        return "none", None
    return "one", delta // b


def next_contact_offset(state: GlobalState, minimum: int = 1) -> int | None:
    """Earliest exact contact offset under unchanged velocities.

    This algebraic event search lets the simulator jump across long empty
    intervals without approximating or omitting any integer-tick contact.
    """

    earliest: int | None = None
    for left_name, right_name in PAIR_ORDER:
        left = state.body(left_name)
        right = state.body(right_name)
        dy = right.y - left.y
        dvy = right.vy - left.vy
        dx = right.x - left.x
        dvx = right.vx - left.vx

        for tangent_dx in (-2, 2):
            y_kind, y_value = _integer_solution(dy, dvy, 0)
            x_kind, x_value = _integer_solution(dx, dvx, tangent_dx)
            if y_kind == "none" or x_kind == "none":
                continue

            constrained = [
                value
                for kind, value in ((y_kind, y_value), (x_kind, x_value))
                if kind == "one" and value is not None
            ]
            if constrained and any(value != constrained[0] for value in constrained[1:]):
                continue
            candidate = constrained[0] if constrained else minimum
            if candidate < minimum:
                continue
            if dy + candidate * dvy != 0:
                continue
            if dx + candidate * dvx != tangent_dx:
                continue
            if earliest is None or candidate < earliest:
                earliest = candidate
    return earliest


def simulate(
    spec: WorldSpec,
    end_tick: int,
    capture_ticks: Iterable[int] = (),
) -> Simulation:
    """Exact event-driven simulation from t0 through end_tick (inclusive)."""

    if end_tick < T0:
        raise ValueError("end_tick must be non-negative")
    requested = frozenset(capture_ticks)
    if any(tick < T0 or tick > end_tick for tick in requested):
        raise ValueError("capture ticks must lie inside the simulated interval")

    captures: dict[int, GlobalState] = {}
    events: list[dict[str, object]] = []
    state = spec.initial
    tick = T0

    while True:
        if tick in requested:
            captures[tick] = state

        after_contacts, local_events = collision_phase(
            state,
            spec.suppressed_pairs_at(tick),
        )
        for event in local_events:
            stamped = {"tick": tick, **event}
            events.append(stamped)

        if tick == end_tick:
            break

        targets = [end_tick]
        targets.extend(candidate for candidate in requested if candidate > tick)
        targets.extend(
            event_tick
            for event_tick, _pair in spec.suppressions
            if event_tick > tick
        )
        contact_offset = next_contact_offset(after_contacts)
        if contact_offset is not None:
            targets.append(tick + contact_offset)

        next_tick = min(target for target in targets if target > tick)
        state = after_contacts.advanced(next_tick - tick)
        tick = next_tick

    return Simulation(captures, tuple(events))


def state_differences(left: GlobalState, right: GlobalState) -> dict[str, list[str]]:
    differences: dict[str, list[str]] = {}
    for name in BODY_NAMES:
        left_body = left.body(name)
        right_body = right.body(name)
        fields = [
            field
            for field in ("x", "y", "vx", "vy")
            if getattr(left_body, field) != getattr(right_body, field)
        ]
        differences[name] = fields
    return differences


def projection_frames(
    spec: WorldSpec,
    body_name: str,
    start_tick: int,
    end_tick: int,
) -> Iterator[tuple[int, int, int, int, int]]:
    """Yield every exact projected frame as tick,x,y,vx,vy."""

    if end_tick < start_tick:
        raise ValueError("end_tick must be at least start_tick")
    start_simulation = simulate(spec, start_tick, (start_tick,))
    state = start_simulation.captures[start_tick]
    after_contacts, events = collision_phase(state, spec.suppressed_pairs_at(start_tick))
    if events:
        raise ValueError("projection window starts on a contact tick")
    next_offset = next_contact_offset(after_contacts)
    if next_offset is not None and start_tick + next_offset <= end_tick:
        raise ValueError("projection window crosses a contact; split it into segments")

    body = state.body(body_name)
    for offset, tick in enumerate(range(start_tick, end_tick + 1)):
        frame = body.advanced(offset)
        yield tick, frame.x, frame.y, frame.vx, frame.vy


def projection_digest(
    spec: WorldSpec,
    body_name: str,
    start_tick: int,
    end_tick: int,
) -> str:
    """Hash every projected frame using >5q: tick,x,y,vx,vy."""

    digest = hashlib.sha256()
    for frame in projection_frames(spec, body_name, start_tick, end_tick):
        digest.update(struct.pack(">5q", *frame))
    return digest.hexdigest()


def compare_projection_frames(
    left: WorldSpec,
    right: WorldSpec,
    body_name: str,
    start_tick: int,
    end_tick: int,
) -> dict[str, int | bool | None]:
    """Compare every frame directly; hashes are receipts, not equality proofs."""

    frames_compared = 0
    mismatch_count = 0
    first_mismatch_tick: int | None = None
    left_frames = projection_frames(left, body_name, start_tick, end_tick)
    right_frames = projection_frames(right, body_name, start_tick, end_tick)
    for left_frame, right_frame in zip(left_frames, right_frames, strict=True):
        frames_compared += 1
        if left_frame != right_frame:
            mismatch_count += 1
            if first_mismatch_tick is None:
                first_mismatch_tick = left_frame[0]
    return {
        "equal": mismatch_count == 0,
        "frames_compared": frames_compared,
        "mismatch_count": mismatch_count,
        "first_mismatch_tick": first_mismatch_tick,
    }


def projection_samples(
    spec: WorldSpec,
    body_name: str,
    ticks: Sequence[int],
) -> dict[str, dict[str, int]]:
    simulation = simulate(spec, max(ticks), ticks)
    return {
        str(tick): simulation.captures[tick].body(body_name).as_dict()
        for tick in ticks
    }


def lineage_trace(events: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """Propagate audit labels with vx swaps; labels are not physical state."""

    lineage = {name: f"{name}.vx@t0-" for name in BODY_NAMES}
    trace: list[dict[str, object]] = []
    for event in events:
        raw_pair = event["pair"]
        if not isinstance(raw_pair, list) or len(raw_pair) != 2:
            raise ValueError("invalid event pair")
        left, right = str(raw_pair[0]), str(raw_pair[1])
        lineage[left], lineage[right] = lineage[right], lineage[left]
        trace.append(
            {
                "tick": event["tick"],
                "pair": [left, right],
                "vx_lineage_after_contact": dict(lineage),
            }
        )
    return trace


def roundtrip_samples() -> list[GlobalState]:
    return [
        matched_initial_state(),
        GlobalState(
            (
                BodyState(-2, 0, 4, 7),
                BodyState(0, 0, -3, 5),
                BodyState(2, 0, 9, -2),
            )
        ),
        GlobalState(
            (
                BodyState(-17, 4, 2, -8),
                BodyState(3, 19, -7, 6),
                BodyState(101, -55, 0, 3),
            )
        ),
    ]


def build_results() -> dict[str, object]:
    specs = world_specs()
    checkpoint_ticks = (T0, 1, T1, T2, T3, T3 + 1, FUTURE_PROBE)
    simulations = {
        name: simulate(spec, FUTURE_PROBE, checkpoint_ticks)
        for name, spec in specs.items()
    }

    late_hashes = {
        name: projection_digest(spec, "B", T1, T2)
        for name, spec in specs.items()
    }
    late_exact_w1_alt = compare_projection_frames(specs["W1"], specs["W_alt"], "B", T1, T2)
    late_exact_w1_w0 = compare_projection_frames(specs["W1"], specs["W0"], "B", T1, T2)
    sample_ticks = (T1, (T1 + T2) // 2, T2)
    late_samples = {
        name: projection_samples(spec, "B", sample_ticks)
        for name, spec in specs.items()
    }

    comparisons: dict[str, object] = {}
    for tick in (1, T1, T2, T3, T3 + 1, FUTURE_PROBE):
        factual = simulations["W1"].captures[tick]
        counterfactual = simulations["W0"].captures[tick]
        comparisons[str(tick)] = {
            "global_states_equal": factual == counterfactual,
            "differing_fields_by_body": state_differences(factual, counterfactual),
        }

    w1_events = simulations["W1"].events
    w0_events = simulations["W0"].events
    alt_events = simulations["W_alt"].events
    w1_lineage = lineage_trace(w1_events)
    alt_lineage = lineage_trace(alt_events)

    roundtrips = [reverse_standard_step(standard_step(sample)[0]) == sample for sample in roundtrip_samples()]
    c_after = {
        name: simulations[name].captures[T3 + 1].body("C").as_dict()
        for name in ("W1", "W0", "W_alt")
    }

    return {
        "schema": "causal-influence-demo/v1",
        "constants": {"t0": T0, "t1": T1, "t2": T2, "t3": T3},
        "model": {
            "space": "unbounded integer lattice Z^2",
            "time": "integer ticks",
            "body_radius": 1,
            "contact_predicate": "same y and absolute center-x separation 2",
            "contact_rule": "fixed-order conditional swap of pair vx; preserve vy",
            "gate_scope": "reversible mathematical tangent gate; all realized witness contacts are approaching",
            "free_flight": "x += vx; y += vy",
            "numeric_domain": "exact integers; no floating point",
            "ordinary_tick_map": "bijective",
            "counterfactual_intervention": "W0 replaces only G_AB with identity at t0",
        },
        "worlds": {
            name: {
                "initial_pre_contact_state": spec.initial.as_dict(),
                "suppressed_contact_gates": [
                    {"tick": tick, "pair": list(pair)}
                    for tick, pair in spec.suppressions
                ],
                "events_through_future_probe": list(simulations[name].events),
            }
            for name, spec in specs.items()
        },
        "late_observation": {
            "observer_projection": "B only: (tick,x,y,vx,vy)",
            "window_inclusive": [T1, T2],
            "frame_count": T2 - T1 + 1,
            "frame_encoding": "struct.pack('>5q', tick, x, y, vx, vy)",
            "sha256_by_world": late_hashes,
            "exact_frame_comparison": {
                "W1_vs_W_alt": late_exact_w1_alt,
                "W1_vs_W0": late_exact_w1_w0,
            },
            "samples_by_world": late_samples,
            "w1_equals_w_alt": late_exact_w1_alt["equal"],
            "w1_equals_w0": late_exact_w1_w0["equal"],
            "identifies_a_b_touch_by_itself": False,
            "non_identifiability_witness": "W1 has A-B contact; W_alt does not; their complete late B projections are identical",
        },
        "full_history_observation": {
            "coverage": "complete A and B contact frame at t0, pre/post velocities, and trusted contact rule",
            "w1_a_b_event_through_t2": [
                event
                for event in w1_events
                if int(event["tick"]) <= T2 and event["pair"] == ["A", "B"]
            ],
            "w_alt_a_b_event_through_t2": [
                event
                for event in alt_events
                if int(event["tick"]) <= T2 and event["pair"] == ["A", "B"]
            ],
            "identifies_touch_within_model": True,
        },
        "matched_counterfactual": {
            "w1_and_w0_pre_contact_states_equal": specs["W1"].initial == specs["W0"].initial,
            "physical_differences": comparisons,
            "c_state_at_t3_plus_1": c_after,
            "effect_reaches_c": c_after["W1"] != c_after["W0"],
        },
        "transmission_trace": {
            "annotation_status": "derived audit labels; not additional physical degrees of freedom",
            "w1": w1_lineage,
            "w_alt": alt_lineage,
            "w1_c_vx_lineage_after_t3": w1_lineage[-1]["vx_lineage_after_contact"]["C"],
            "w_alt_c_vx_lineage_after_t3": alt_lineage[-1]["vx_lineage_after_contact"]["C"],
        },
        "proof_checks": {
            "standard_step_roundtrip_samples": roundtrips,
            "all_roundtrip_samples_pass": all(roundtrips),
            "w1_w0_distinct_at_every_reported_future_checkpoint": all(
                not item["global_states_equal"]  # type: ignore[index]
                for item in comparisons.values()
            ),
            "future_probe_tick_is_example_not_proof": FUTURE_PROBE,
            "proof_method": "injectivity plus contradiction by repeated inverse application",
            "closed_form_trajectory": {
                "for_1_le_n_le_t3": {
                    "W1_A": "(-1,n,0,1)",
                    "W1_B": "(n+1,-n,1,-1)",
                    "W0_A": "(n-1,n,1,1)",
                    "W0_B": "(1,-n,0,-1)",
                },
                "for_n_ge_t3_plus_1": {
                    "W1_A": "(-1,n,0,1)",
                    "W1_B": "(t3+1,-n,0,-1)",
                    "W1_C": "(n+3,-t3,1,0)",
                    "W0_A": "(n-1,n,1,1)",
                    "W0_B": "(1,-n,0,-1)",
                    "W0_C": "(t3+3,-t3,0,0)",
                },
            },
        },
        "limits": [
            "The global persistence theorem is conditional on deterministic injective closed dynamics.",
            "Injectivity of the global state does not imply persistent identifiability in a subsystem projection.",
            "Per-body persistence is verified for this constructed trajectory, not inferred from injectivity alone.",
            "The full-history attribution is exact only within the specified model and trusted observation coverage.",
            "No claim is made that the physical cosmos is exactly closed, injective, noiseless, or reconstructable.",
            "The reversible tangent gate is a mathematical rule, not a general rigid-body collision simulator; every contact on the demonstrated trajectory is approaching.",
            "Forever means every finite future tick under the model, not an empirical measurement of infinite time.",
        ],
    }


def render_results_json() -> str:
    return json.dumps(build_results(), indent=2, sort_keys=True) + "\n"


def checkpoint_rows() -> list[dict[str, object]]:
    ticks = (T0, 1, T1, T2, T3, T3 + 1, FUTURE_PROBE)
    rows: list[dict[str, object]] = []
    for world_name, spec in world_specs().items():
        simulation = simulate(spec, FUTURE_PROBE, ticks)
        for tick in ticks:
            state = simulation.captures[tick]
            for body_name in BODY_NAMES:
                body = state.body(body_name)
                rows.append(
                    {
                        "world": world_name,
                        "tick": tick,
                        "phase": "pre_contact",
                        "body": body_name,
                        "x": body.x,
                        "y": body.y,
                        "vx": body.vx,
                        "vy": body.vy,
                    }
                )
    return rows


def render_checkpoints_csv() -> str:
    output = io.StringIO(newline="")
    fieldnames = ("world", "tick", "phase", "body", "x", "y", "vx", "vy")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(checkpoint_rows())
    return output.getvalue()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_receipt(root: Path) -> str:
    return "".join(
        f"{sha256_file(root / member)}  {member.as_posix()}\n"
        for member in sorted(RECEIPT_MEMBERS, key=lambda item: item.as_posix())
    )


def write_artifacts(root: Path) -> None:
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (root / RESULTS_PATH).write_text(render_results_json(), encoding="utf-8", newline="\n")
    (root / CHECKPOINTS_PATH).write_text(render_checkpoints_csv(), encoding="utf-8", newline="\n")
    (root / RECEIPT_PATH).write_text(render_receipt(root), encoding="ascii", newline="\n")


def verify_artifacts(root: Path) -> dict[str, object]:
    expected_payloads = {
        RESULTS_PATH: render_results_json().encode("utf-8"),
        CHECKPOINTS_PATH: render_checkpoints_csv().encode("utf-8"),
    }
    payload_matches = {
        path.as_posix(): (root / path).is_file() and (root / path).read_bytes() == expected
        for path, expected in expected_payloads.items()
    }
    receipt_file = root / RECEIPT_PATH
    receipt_matches = receipt_file.is_file() and receipt_file.read_text(encoding="ascii") == render_receipt(root)
    passed = all(payload_matches.values()) and receipt_matches
    return {
        "passed": passed,
        "generated_payloads_match": payload_matches,
        "receipt_matches": receipt_matches,
    }


def concise_summary(results: Mapping[str, object]) -> dict[str, object]:
    late = results["late_observation"]
    counterfactual = results["matched_counterfactual"]
    proof = results["proof_checks"]
    transmission = results["transmission_trace"]
    if not all(isinstance(item, Mapping) for item in (late, counterfactual, proof, transmission)):
        raise TypeError("unexpected results structure")
    return {
        "late_W1_equals_W_alt": late["w1_equals_w_alt"],  # type: ignore[index]
        "late_observation_identifies_A_B_touch": late["identifies_a_b_touch_by_itself"],  # type: ignore[index]
        "matched_counterfactual_effect_reaches_C": counterfactual["effect_reaches_c"],  # type: ignore[index]
        "W1_C_vx_lineage_after_t3": transmission["w1_c_vx_lineage_after_t3"],  # type: ignore[index]
        "roundtrip_checks_pass": proof["all_roundtrip_samples_pass"],  # type: ignore[index]
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write-artifacts", action="store_true")
    action.add_argument("--verify", action="store_true")
    action.add_argument("--print-results", action="store_true")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent
    if args.write_artifacts:
        write_artifacts(root)
        print(json.dumps({"written": [RESULTS_PATH.as_posix(), CHECKPOINTS_PATH.as_posix(), RECEIPT_PATH.as_posix()]}))
        return 0
    if args.verify:
        verification = verify_artifacts(root)
        print(json.dumps(verification, indent=2, sort_keys=True))
        return 0 if verification["passed"] else 1

    results = build_results()
    if args.print_results:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        print(json.dumps(concise_summary(results), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
