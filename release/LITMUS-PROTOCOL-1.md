# THE LITMUS PROTOCOL
# i64. Version 1. Pure ASCII.

This is a protocol you run yourself, in your own words. Nothing in
it is scripted by us, and that is the point: a scripted demo would
prove only that a script runs. You bring the prompts.

## What you need

A running bob instance (a deterministic local model runtime built
on the design described in the white paper), with the /new command
available, and the ability to start a fresh process twice.

## The four steps

1. FRESH-RUN REPRODUCTION. From a clean start, ask anything you
   like (any prompt class - a haiku, a question, a task). Save the
   response bytes. Start a second clean process from the same state
   and ask the identical prompt. The two responses must match BYTE
   FOR BYTE.

2. IN-CONVERSATION NOVELTY. In one continuing conversation, ask the
   identical prompt a second time. The response must be NEW - not a
   replay of the first. (State advanced; the mapping is
   deterministic over state plus input, not over input alone.)

3. THE RESET. Issue /new, then ask the identical prompt again. The
   response must reproduce the FIRST response's exact bytes. bob
   does not tell you he is deterministic; he shows you.

4. INDEPENDENT REPETITION. Repeat steps 1-3 in two clean processes.
   Every limb must reproduce.

## What a pass proves

Deterministic state-plus-input execution with conversational
continuity: the same memory and the same words produce the same
bytes, every time, and the conversation still moves.

## What a pass does not prove

Nothing about quality, safety, or fitness for any purpose. A
chatbot with a temperature of zero is also deterministic on a
single turn; the protocol's second and third steps are what
separate a continuing deterministic system from a stateless one.
Run the protocol against a cloud chat model and watch where it
fails.
