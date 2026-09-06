This repository is finished. It is the published record behind one paper, so the
numbers in it are not to be recomputed, tidied or improved — they are the result.

Everything you can import lives in `src/steering`. Everything you run lives in
`scripts`. Install the package with `pip install -e .` and import it normally; if you
find yourself adding a directory to the import path, something is in the wrong place.

Three checks decide whether a change is safe, and all three have to stay green:
`python -m pytest tests`, `python scripts/audit_repo.py`, and the checker in the paper
repository, which reads about two hundred files here and refuses if any reported number
has moved. Run all three before and after anything you touch, and compare the counts.

The simulator lies when it is unwell. It keeps answering, keeps reporting plausible
speeds, and quietly stops advancing the physics, and nothing in the resulting data shows
which server produced it. So restart it before every measurement run rather than when
something looks wrong, never stop a client with kill minus nine, and never let two
clients talk to one port at once. A run that ends after a handful of steps is a bug and
not a pass.

The simulator also applies most changes on the following tick. Weather, camera moves and
sensor images all land one step later, and nothing raises an error when you read them too
early. Build the state you want, do not read it back.

Driving the same policy twice does not give the same trajectory, so every closed-loop
number here is a rate over repeated laps rather than a single run. If two laps of one
cell disagree, that is a defect to find, not a reason to drive more laps.

The certificates are reproducible without the simulator, which is how most people will
check this work. The captured images that make that possible are too large for this
repository and are published separately; `scripts/fetch_captures.py` retrieves them.
