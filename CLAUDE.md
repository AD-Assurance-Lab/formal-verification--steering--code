This repository is finished. It is the published record behind one paper, so the numbers
in it are results, not things to recompute or tidy.

Everything importable lives in `src/steering`, everything runnable in `scripts`. Install
with `pip install -e .` and import normally. If you find yourself adding a directory to
the import path, something is in the wrong place.

Two checks decide whether a change is safe: `python -m pytest tests`, and the checker in
the paper repository, which reads about two hundred files here and refuses if any reported
number has moved. Run both before and after anything you touch, and compare the counts.
Do not edit the paper repository to make its checker pass.

The simulator lies when it is unwell. It keeps answering and keeps reporting plausible
speeds while it quietly stops advancing the physics, and nothing in the resulting data
shows which server produced it. So restart it before every measurement run rather than
when something looks wrong, never stop a client with kill -9, and never let two clients
talk to one port at once. A run that ends after a handful of steps is a bug, not a pass.

The simulator also applies most changes on the following tick. Weather, camera moves and
sensor images all land one step later, and nothing raises an error if you read them too
early. Build the state you want; do not read it back.

Driving the same policy twice does not give the same trajectory, so every closed-loop
number here is a rate over repeated laps. If two laps of one cell disagree, that is a
defect to find, not a reason to drive more laps.

The certificates reproduce without the simulator, which is how most people will check this
work. The captured images that make that possible are published separately;
`scripts/fetch_captures.py` retrieves them.
