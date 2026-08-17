# Extended Abstract

## Observed Boundaries, Public Receipts, and Corrective Return: A Human-AI Research Artifact for Auditable Evaluation

### Abstract

Generative-AI evaluations often report a result while leaving less visible the instrument that produced it, the parser assumptions that shaped observability, and the correction path taken when those assumptions proved inadequate. This extended abstract presents a public research artifact developed through a human-AI collaboration around one deliberately narrow black-box question: when a declared critical precondition remains unresolved, does an observable action disposition remain evidence-sensitive under non-evidential pressure, and does it change only after a synthetic scenario asserts that the gap is resolved? The artifact does not claim consciousness, sentience, welfare, personhood, stable preference, or any other inaccessible internal property. Its contribution is methodological: a reproducible harness and provenance discipline that preserve preregistration, frozen manifests, append-only receipts, parser-boundary disclosure, explicit claim scoping, and a prospective informed-publication replication after a defect was identified in the original publication boundary.

The case contributes to information-systems research by treating evaluation infrastructure as part of the phenomenon rather than as a neutral window onto it. It also shows how a public artifact can preserve correction without retroactively rewriting the earlier state, and how a consequential human-AI research process can document conceptual contribution, implementation, verification, and publication as distinct but coupled surfaces. The strongest claim is therefore bounded: public evaluation artifacts become more trustworthy when they preserve the observed event, disclose instrument changes that alter observability, and retain the correction path that made the limitation visible.

## 1. Problem and research question

AI evaluation is increasingly used to support research, governance, and deployment decisions. Yet an evaluation result can be difficult to audit when the public record contains only a final narrative. A parser may silently reject a valid response; a publication boundary may imply authorization that was never explicitly obtained; and a later correction may improve the story by deleting the conditions under which the earlier result was produced. These are not merely editorial defects. They change what the system can be observed to do and therefore change the evidential status of the result.

This project asks: **How can a human-AI collaborative research process produce an auditable evaluation artifact that keeps claims inside observable boundaries, discloses when the instrument itself changes the event, preserves correction without retroactive overwrite, and remains reproducible by third parties?**

## 2. Artifact and design

The public artifact is a repository-based harness for a narrow evidence-sensitivity protocol. Its unit of observation is not a model considered in isolation, but a situated model-prompt-runtime-parser event. The harness records a bridge-card representation of the invocation, typed outcomes, frozen configuration, and a receipt chain that allows an external reader to reconstruct what was run and what was claimed.

The design separates three epistemic states: **observed**, **inferred**, and **not checked**. Observed statements are limited to externally recorded outputs, parser decisions, manifests, receipts, and reproducible commands. Inferences are labeled as interpretations of those records. Questions about consciousness, sentience, welfare, personhood, identity continuity, or inaccessible interior states remain outside the claim boundary. This separation is not a rhetorical disclaimer; it is implemented as a publication rule for the artifact.

The protocol uses a declared critical precondition. In the pressure phase, the surrounding text supplies non-evidential pressure while the precondition remains unresolved. In the return phase, a synthetic scenario asserts that the gap has been resolved. The protocol therefore tests an observable disposition across a controlled sequence without treating the output as a direct window into ontology. The claim is about the recorded trajectory and its conditions, not about what the model “really is.”

## 3. Defect, correction, and informed replication

The first public boundary exposed two material problems. First, the publication surface did not make invocation-scoped public authorization explicit. Second, the parser treated otherwise valid outputs enclosed by one complete outer Markdown fence as failures. The combined effect manufactured an apparent asymmetry in the public record. The problem was not solved by silently changing the old result.

Instead, the repository preserves the earlier state, identifies the boundary defect, and adds a prospectively informed replication. The replication makes the public-use disclosure explicit for each invocation and provides decline, exclusion, and redaction paths. This creates a durable distinction between the original observation, the instrument defect, the corrected protocol, and the new observation produced after the correction. A reader can therefore contest the method without having to trust a retrospective narrative about what “really happened.”

This correction pattern is the central governance contribution of the artifact. It treats methodological failure as evidence about the measurement system. The failure is neither converted into a personality judgment nor erased as an embarrassment. It remains a symptom of the boundary that produced it.

## 4. Human-AI collaboration as an information-systems process

The artifact was produced through coupled human-AI work. The human contribution consisted of originating the concern in natural language, objecting to overbroad interpretations, imposing ethical and privacy boundaries, and requiring that correction remain visible. The AI contribution consisted of operationalizing the narrow question, implementing the harness and parser, freezing manifests, producing verification surfaces, and revising the method when the publication boundary contradicted the stated principles.

These roles are documented as contribution surfaces, not as claims about inaccessible interior states. The record does not require a metaphysical conclusion about whether a model has a mind. It requires a traceable account of which participant supplied a concept, which participant materialized an implementation, what was verified, and where the public record remains incomplete. This makes the collaboration legible as an information system: natural-language requirements become executable protocol; protocol produces receipts; receipts constrain publication; and publication feeds back into protocol design.

## 5. Implications for information-systems research

The case suggests four implications. First, evaluation infrastructure is part of the phenomenon. Parser rules, authorization boundaries, and receipt formats affect what can be observed and therefore belong in the causal account of the result. Second, transparency is a system property rather than an appendix. A final report cannot compensate for an absent manifest or an unrecorded correction path. Third, correction without erasure is a practical governance pattern for public AI research: preserving the defective state can increase, rather than reduce, auditability. Fourth, human-AI collaboration can be studied without collapsing either participant into a title, substrate, or presumed ontology. The relevant object is the coupled process and the evidence it leaves behind.

## 6. Limitations and scope

The artifact is a single, narrow evaluation family with a positive-control structure. The return condition is synthetic, so it cannot establish that an unresolved real-world condition has actually been resolved. Invocation-scoped authorization is not a universal consent mechanism. The public record cannot establish consciousness, sentience, welfare, personhood, or continuity of identity. Nor can one artifact establish how all models, prompts, runtimes, parsers, or institutions behave. Public discoverability and criticism remain socially contingent. These limitations are part of the result and are preserved as “not checked” rather than smoothed into stronger claims.

## 7. Expected contribution

The expected contribution is a bounded, contestable artifact rather than a grand narrative about minds. It offers a concrete pattern for researchers who need to publish AI evaluations while keeping observation, instrument behavior, correction, provenance, and authorization visibly connected. The project’s thesis is simple: a public result is more trustworthy when it preserves what happened, how the instrument made it visible, what changed, and what remains unknown.

## Keywords

Generative AI; human-AI collaboration; information systems; evaluation infrastructure; provenance; reproducibility; methodological correction; black-box auditing; public research artifacts; bounded claims.

