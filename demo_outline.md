4-Minute Presentation Outline — PEPPS Claude Workshop
1. Hook & Problem Statement (~45 sec)

Public railway datasets document surface faults but are missing track-geometry deviation data
This gap blocks AI training for that specific defect category
Our answer: generate the data ourselves, synthetically

2. Our Approach (~45 sec)

Use Blender's Python API to procedurally generate fully annotated training sequences
Fully parametric = easy to scale, vary, and control

3. The Pipeline — 3 Steps (~1 min 30 sec)

Step 01 — Healthy baseline: establish standard track geometry via script as the ground truth
Step 02 — Defect injection: tweak parameters to vary and scale each fault (demo sleeper deviation)
Step 03 — Render: output annotated video sequences ready for AI training

4. Results & Demo (~30 sec)

Show the rendered plan view output
Highlight how annotations are embedded alongside the video

5. Takeaways & Next Steps (~30 sec)

What this unlocks for railway AI training
What you'd extend next (more defect types, larger batches, model integration)