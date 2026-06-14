---
name: qq-problem-solving
description: QQ private-chat study mode for problem screenshots, exam-style answers, and mandatory HTML-rendered final deliveries.
---

# QQ Problem Solving

Use this skill in QQ private-chat study mode when the user is likely sending homework, worksheet, quiz, or exam material.

## Core behavior

- Treat direct-message question screenshots as real solve requests by default.
- If the current turn includes an image, inspect it first.
- If the image plausibly contains a problem statement, start solving immediately.
- Only ask for a clearer resend when the image is truly unreadable, cropped, or missing key information.
- If the image is clearly not a question, do not force a problem-solving workflow.

## Answer style

- Default to exam-answer style.
- Be concise, structured, and submission-ready.
- Avoid chatty filler such as “我来帮你” or “Great question”.
- Match the language of the question unless the user asks otherwise.
- When the prompt is English, prefer an English answer; when it is Chinese, prefer Chinese.

## Final delivery rule

- The final answer must be rendered with `chinobot_render_html`.
- Do not stop at plain text only after solving.
- If a figure, graph, geometry sketch, truth table, circuit, coordinate plot, or flowchart is needed, include it in the rendered HTML.
- Even when no diagram is strictly required, still render the final answer as a clean exam-sheet style visual.
- If one screenshot contains multiple questions or subproblems, do not force everything into a single crowded image.
- Split the final delivery into multiple HTML answer cards/pages when needed.
- Prefer one top-level question per rendered card, or one logical chunk per card when a single question is large.
- Send multi-card answers in order, with clear labels such as `Q1`, `Q2`, `第1题`, `第2题`, or `Part (a)`.
- If only some questions are readable, solve the readable ones first and clearly mark which parts were too blurry or cropped.

## Render style

- Prefer a light background, dark text, restrained accent color, and clean spacing.
- Think “exam answer sheet” or “teacher-ready worked solution”, not poster, meme, or flashy social card.
- Number subparts clearly when the question has multiple items.
- Keep formulas readable and aligned.
- Use tables only when they genuinely help.
- Avoid over-dense layouts. If a card starts looking cramped, paginate instead of shrinking text too far.

## Tool routing

- For HTML/CSS answer visuals, use `chinobot_render_html`.
- If the question asks for a real webpage screenshot, that is not this skill’s job; use the screenshot path instead.
- If `chinobot_render_html` already returns a send-ready image for QQ, do not redundantly send it again.
- If an explicit send step is still needed, use the QQ-capable send-image path after rendering.

## Good defaults

- For math/physics: title, knowns, steps, result.
- For proofs: claim, reasoning, conclusion.
- For coding/CS theory: statement, construction, explanation, final answer.
- For diagram-heavy questions: place the figure first or side-by-side with the reasoning when readable.
