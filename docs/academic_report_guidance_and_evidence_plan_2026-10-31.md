# Academic Report Guidance and Evidence Plan

**Project:** Intelligent Robotics for Energy Infrastructure — Design Project  
**Date prepared:** 2026-10-31  
**Purpose:** Preserve University of Aberdeen academic-writing guidance and a provisional report structure for later use after the core technical deliverables are complete.

## 1. Status and authority

This file is **planning guidance only**.

The source hierarchy for the eventual assessed report should be:

1. Any course-specific assessment brief, marking rubric, word-count rule, template, or Blackboard instruction for this module.
2. Direct instructions from the course coordinator/professor.
3. University of Aberdeen general academic-writing, referencing, academic-integrity, and scientific-report guidance.
4. This planning document.

If a later module-specific instruction conflicts with anything below, the module-specific instruction overrides it.

At the time this file was prepared, no public course-specific report template had been identified. The structure below is therefore provisional.

## 2. Evidence that a report is expected

The course coordinator has explicitly referred to the need to justify and document neural-network design choices in **the report**.

In the professor's 2026-10-25 reply concerning autonomous-navigation stability, he explained that final robot behaviour depends on factors including:

- turning radius/curvature;
- travelling speed;
- amount of training data;
- distribution of training data;
- quality of training data;
- neural-network architecture;
- random initialisation.

He further stated that a CNN is not required for the exercise and that an unnecessarily complex NN architecture can worsen robot behaviour and reduce the final grade unless there is a proper reason and the choice is properly justified and documented in the report.

This is strong project-specific evidence that technical decisions, experimental rationale, and justification should be preserved for later academic writing.

## 3. University of Aberdeen general academic-writing principles

The University of Aberdeen Student Learning Service guidance emphasises that successful academic writing depends on:

- critical thinking;
- clear structure;
- effective use of sources;
- grammatically correct and appropriately formal English;
- a clear purpose and line of argument;
- evidence-based claims;
- coherent paragraphing;
- conclusions that follow from the evidence.

The University's academic-writing material also emphasises that arguments should be clear, well reasoned and persuasive, supported by appropriate evidence, and should acknowledge counter-arguments where relevant.

### Practical consequence for this project

The eventual report should not be a chronological diary of every action taken.

Instead it should explain:

1. what the project required;
2. what engineering decisions were made;
3. why those decisions were made;
4. what evidence was produced;
5. what failed and why that mattered;
6. what was changed in response;
7. what final system was achieved;
8. what limitations remain;
9. what conclusions are justified by the results.

## 4. University of Aberdeen scientific-report structure

A University of Aberdeen scientific-report guide describes a conventional formal report as containing:

- Title
- Author/affiliation information where required
- Abstract
- Introduction
- Methods
- Results
- Discussion
- Conclusion
- References/Bibliography
- Appendices where appropriate

The same guidance stresses the distinction between **Results** and **Discussion**:

- Results should state clearly what happened and present evidence such as figures, tables, graphs, measurements, and observations.
- Discussion should interpret those results, explain their meaning, compare them with expectations or prior work, and examine disagreements or limitations.

### Provisional project-specific structure

Subject to the actual module rubric, a strong structure for this robotics project could be:

1. **Title page**
2. **Abstract**
3. **Introduction and project objectives**
4. **System and simulation environment**
   - Pioneer P3DX / CoppeliaSim scene
   - Python
   - ZMQ Remote API
   - OpenCV
   - Google Colab
5. **Methodology**
   - Step 1: Python-CoppeliaSim communication
   - Step 2: manual W/A/D control and motion calibration
   - Step 3: camera streaming/OpenCV
   - Step 4: training-data collection
   - Step 5: neural-network design and training
   - Step 6: autonomous navigation
   - Step 7: ultrasonic sensing and mapping
6. **Experimental design and calibration**
   - speed;
   - turning curvature;
   - data amount/distribution/quality;
   - model architecture;
   - initialisation;
   - validation strategy.
7. **Results**
   - manual-control validation;
   - dataset statistics;
   - model-training results;
   - autonomous-navigation results;
   - sensor/mapping results.
8. **Discussion**
   - interpretation of behaviour;
   - why the original CNN/controller approach was over-complex;
   - why the simplified baseline was chosen;
   - comparison of offline ML metrics with live closed-loop behaviour;
   - simulator instability and reproducibility limitations;
   - engineering trade-offs and resource/cost management;
   - remaining limitations.
9. **Conclusion**
10. **References**
11. **Appendices**
   - supplementary figures/tables;
   - configuration values;
   - selected logs;
   - extra diagnostics;
   - evidence that would interrupt the main narrative if placed in the body.

This structure must be revised when a course-specific word count, template, or marking rubric becomes available.

## 5. Academic-writing treatment of the simulator failures

The CoppeliaSim crashes and AirGPU fallback problems should be retained as academically useful engineering evidence, but they should be framed carefully.

### Appropriate academic framing

Use them to discuss:

- experimental-environment reliability;
- reproducibility;
- limitations of the validation environment;
- evidence-based troubleshooting;
- decision making under uncertainty;
- system-level rather than model-only diagnosis;
- resource and cost constraints;
- risk management;
- reasons for pausing or changing an execution environment.

### Avoid

Do not:

- present crashes as an excuse for incomplete work;
- claim a confirmed CoppeliaSim defect without authoritative evidence;
- attribute root cause to Python, the `keyboard` library, Windows, or hardware unless evidence supports it;
- claim another student's similar report proves a course-wide software defect;
- exaggerate the AirGPU issue beyond the observed Moonlight connection failure.

### Current evidence to preserve

Existing repository evidence includes:

- repeated CoppeliaSim 4.7 instability;
- Windows crash signature involving `ntdll.dll` and exception `0xc0000374`;
- initial improvement with CoppeliaSim 4.9.0 rev6;
- later crash during longer/full-maze traversal;
- clean-reboot/minimal-software retry still failing;
- accepted Step-2 motion profile;
- inability to complete two reliable full-maze Step-2 traversals;
- another student's similar key-hold/key-control crash report;
- AirGPU cloud fallback;
- Moonlight failure before pairing;
- bounded cost-control decisions;
- AirGPU support escalation.

The detailed source-of-truth record is:
`docs/simulator_instability_step02_blocker_2026-10-31.md`

## 6. Referencing and source acknowledgement

University of Aberdeen Library guidance requires acknowledgement when:

- quoting another person's words;
- paraphrasing another person's ideas;
- using another person's data;
- using charts, diagrams, figures or images created by others;
- using external evidence that informs the analysis.

The University notes that referencing styles vary and that the required style should be confirmed with the course coordinator/supervisor.

### Project rule

Do **not** choose Harvard, IEEE, Vancouver, or another style merely because it is convenient.

Wait for:

- the module brief;
- School/discipline guidance;
- or explicit professor instructions.

Once the required style is known, normalize all references to that style.

## 7. Academic integrity and use of GenAI

University of Aberdeen academic-integrity guidance states that assessed work should be prepared honestly and independently, that sources must be acknowledged, and that GenAI use such as ChatGPT must be appropriately referenced/acknowledged where applicable.

This is important for this project because AI tools have been used for:

- planning;
- debugging support;
- interpretation;
- code review;
- documentation support;
- project decision-making.

### Required precaution before final report drafting

Before preparing submission-ready report prose:

1. check the current module-specific GenAI rules;
2. determine whether AI-assisted drafting is permitted;
3. determine what acknowledgement/citation/disclosure is required;
4. preserve an audit trail of the student's own engineering decisions, experiments, code, observations and interpretation;
5. ensure the final assessed work accurately reflects the student's own understanding.

This repository can support that audit trail because it preserves:

- commits;
- branch history;
- experiment documentation;
- code changes;
- test evidence;
- simulator diagnostics;
- decision records.

## 8. Evidence-preservation plan for the eventual report

From this point onward, preserve the following whenever materially relevant.

### Experimental configuration

Record:

- CoppeliaSim version;
- scene version;
- motion profile;
- Python version;
- dependency versions where relevant;
- model architecture;
- random seed;
- dataset counts;
- split strategy;
- controller settings.

### Results

Preserve:

- test outputs;
- class distributions;
- training curves;
- confusion matrices where used;
- live traversal outcomes;
- navigation failures/successes;
- mapping outputs;
- timing/latency observations if relevant.

### Decision rationale

Record why major choices were made, including:

- abandoning aggressive point turns;
- reducing speed;
- recollecting data;
- preferring a simple perceptron;
- avoiding unnecessary controller heuristics;
- rejecting unstable execution environments;
- using or rejecting cloud fallbacks.

### Negative results

Preserve failed approaches when they materially explain the final design.

Examples:

- historical CNN variants;
- over-weighting turns;
- autonomous oscillation;
- long turn commitment;
- simulator crashes;
- inaccessible AirGPU desktop.

Negative results should be summarized selectively in the report rather than reproduced exhaustively.

## 9. Writing-quality checklist

Before final submission, verify that:

- every section has a clear purpose;
- claims are supported by evidence;
- observations and interpretations are distinguished;
- Results and Discussion are not conflated;
- figures/tables are numbered and referred to in the text;
- captions are informative;
- abbreviations are defined;
- terminology is consistent;
- technical choices are justified;
- limitations are explicit;
- conclusions follow from results;
- references are complete and consistent;
- no unsupported claim of root cause is made;
- the report is proofread for grammar, clarity and concision;
- any permitted GenAI use is acknowledged according to current course/University requirements.

## 10. Aberdeen sources reviewed

### Student Learning Service — Improving Your Writing

University of Aberdeen, Student Learning Service.  
URL: https://www.abdn.ac.uk/toolkit/documents/uploads/improving_your_writing.pdf

Use for:

- general academic-writing quality;
- structure;
- paragraphing;
- critical thinking;
- editing;
- source use.

### Student Transitions — Academic Writing at University

University of Aberdeen / Student Learning Service / Centre for Academic Development.  
URL: https://www.abdn.ac.uk/media/site/staffnet/content-images/Academic_Writing.pdf

Use for:

- coherent academic style;
- evidence-based argument;
- clarity;
- structure;
- critical thinking.

### Using Word to Write a Report — University of Aberdeen computing/scientific-report guidance

University of Aberdeen.  
URL: https://homepages.abdn.ac.uk/nph120/meteo/wordrprt.pdf

Use as **general scientific-report guidance only**, not as a module template.

Useful principles include:

- Title;
- Abstract;
- Introduction;
- Methods;
- Results;
- Discussion;
- Conclusion;
- References;
- Appendices;
- clear figure numbering/captions;
- following course-specific instructions when available.

### Avoiding Plagiarism

University of Aberdeen Library.  
URL: https://www.abdn.ac.uk/media/site/library/documents/guides/qggen027.pdf

Use for:

- source acknowledgement;
- quoting/paraphrasing;
- reference lists/bibliographies;
- checking the required referencing style with the course coordinator.

### Ensuring Academic Integrity in Assessments — Advice and Guidance for Students

University of Aberdeen, Centre for Academic Development.  
URL: https://www.abdn.ac.uk/media/site/staffnet/documents/Ensuring_Academic_Integrity_in_Assessments_-_Advice_and_Guidance_for_Students_Infographic_August_2023.pdf

Use for:

- independent assessed work;
- plagiarism avoidance;
- data integrity;
- referencing;
- GenAI acknowledgement;
- seeking course-coordinator guidance when assessment rules are uncertain.

## 11. Next academic-writing gate

Do not begin final submission-ready report drafting yet.

Resume formal report preparation when:

1. the core technical deliverables are substantially complete; and
2. the course-specific report instructions, rubric, template, word count or submission rules have been located or confirmed.

Until then, continue preserving evidence so the eventual report can be written from verified project records rather than reconstructed from memory.
