# formal-verification--steering--code

This repository is finished. It is the published record behind one paper. The
numbers in it are results. Do not recompute them and do not tidy them.

## Layout

Importable code goes in `src/steering`. Runnable code goes in `scripts`. Install
with `pip install -e .` and import normally. If you must add a directory to the
import path, the file is in the wrong place.

## Run two checks before and after any change

1. `pytest tests`.
2. The checker in the paper repository. It reads about 200 files here. It fails
   if a reported number moves.

Compare the counts from before and after.

## Never edit the paper repository

Do not edit `formal-verification--steering--arxiv` and do not commit to it. Read
it when you must. Zach writes those papers and he reviews them himself.

If a change here breaks the paper, do this:

1. Copy the paper repository to the scratchpad.
2. Patch the copy and verify it.
3. Tell Zach the exact change to make, and what breaks if he does not make it.

## The simulator lies when it is unwell

CARLA keeps answering, and it keeps reporting sensible speeds, after it stops
advancing the physics. The data does not show which server made it. So:

- Restart the server before every measurement run.
- Never stop a client with `kill -9`.
- Never let two clients use one port.
- Treat a run that ends after a few steps as a bug, not as a pass.

## The simulator applies a change on the next tick

Weather, camera moves and sensor images all land one step late. Nothing raises an
error if you read them too early. Set the state you want. Do not read it back.

## Closed-loop numbers

The same policy driven twice gives a different path. Every closed-loop number
here is a rate over repeated laps. If two laps of one cell disagree, find the
defect. Do not drive more laps.

## Certificates

The certificates reproduce without the simulator. Most readers check the work
that way. `scripts/fetch_captures.py` gets the captured images.

A full 12-cell run of `scripts/verify/certify_sustained_bound.py` takes about an hour
on this machine's RTX 5090. Each cell takes 5 to 6 minutes.

The shell working directory resets between commands. Change directory inside each
command.
