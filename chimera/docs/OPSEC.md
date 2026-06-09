# CHIMERA — Operator Security Discipline (OPSEC)

> Living document. v1.0. Updated as practice evolves.
> Companion to ARCHITECTURE.md §8 (Security Model).
> Updated: 2026-06-09

---

## Why this document exists

ARCHITECTURE.md §8 invariant I7 states: "operator owns the consequence". Every security invariant CHIMERA enforces holds ONLY if the operator does not defeat it through behavior. The strongest fortress is opened by the owner.

This file is the operator's contract with themselves. It is not advice; it is the discipline that makes the technical architecture meaningful.

Read it. Disagree with parts. Edit it. But keep one — yours, written by you, kept current.

The tone is imperative on purpose. Under stress, the brain looks for rules, not nuance.

---

## 1. The two-persona discipline

CHIMERA assumes the operator maintains separation between two distinct personas:

- **Persona A** — work, known identity. Google, banking, ABI client work, Samsung Galaxy, real name, normal life.
- **Persona B** — anonymous. Research, private browsing, accounts with no real-name link. Tor always.

These two NEVER touch. One slip ends Persona B forever.

### Red lines that kill Persona B forever

- Logging into ANY Persona-A account (Gmail, bank, Samsung) from B
- Opening a file in A that was downloaded in B (the file may phone home)
- Using the same writing style, username, or distinctive phrasing
- Browsing the same sites at the same time of day in both
- Persona-B traffic without Tor through your home WiFi
- Pairing Persona-B activity with the Samsung over Bluetooth

### The Samsung Galaxy is Persona A

It cannot become Persona B. Not after factory reset, not after new SIM, not "just for this one thing". Android is Google at the OS level plus Samsung's own telemetry plus a baseband processor that always knows your location. If Persona B ever needs a phone, that is a different physical device (Pixel + GrapheneOS, or no phone at all).

### Persona-B writing discipline

The hardest invariant to maintain. Stylometry — your phrasing rhythm, sentence length, idiom choice — survives translation and renaming. If Persona B writes like Persona A, the personas are linked.

Practical techniques:
- Draft in a second language when fluent, then translate if needed
- Use shorter or longer sentences than your natural pattern, consistently
- Avoid signature phrases, jokes, references that are recognizably yours
- Re-read drafts and remove anything that "sounds like you"

---

## 2. Override-phrase hygiene

CHIMERA has master phrases for VAULT unlock, PURGE arming, TETHER L3 arming, and PULSE override. These phrases are the entire security model — everything below depends on them.

### Rules

- Different phrase per system. Never reuse a VAULT phrase for PURGE.
- Long: 16+ characters minimum. Not memorable in the password-manager sense.
- Stored in your head. Possibly written ONCE on paper in a place only you know — never in any digital form, never in 1Password, never in iCloud Notes, never in a file on this machine.
- Practice typing each phrase weekly so muscle memory survives stress.
- If you forget one, you lose what it protected. By design. (ARCHITECTURE I7.)

### Rotation triggers

- Annually as default hygiene
- Immediately if you typed a phrase on a machine you do not fully trust
- Immediately if you suspect shoulder surveillance during typing
- Immediately after any panic event (border stop, device out of sight)

---

## 3. Panic-gesture practice

PURGE has a physical panic trigger — hotkey-hold or power-button pattern. TETHER L3 is the automatic version. Both can destroy data irreversibly.

### Required practice

- Run `purge.test` (dry-run) before AND after every `purge.arm`
- Physically rehearse the panic gesture monthly, with PURGE DISARMED
- Time yourself: from moment-of-decision to trigger should be under 5 seconds
- Stress changes motor skills. Untrained gestures fail under adrenaline.

### Never

- Arm PURGE for the first time without one dry-run
- Re-arm PURGE after a long disarmed period without a fresh dry-run
- Arm PURGE during a high-emotion event ("they're coming, let me arm it now")

The panic gesture only protects you if it is practiced. Otherwise it is just a way to lose data when you fumble.

---

## 4. Persona-B environment hygiene

When operating as Persona B:

- **Tor Browser is the ONLY browser.** No exceptions, not even "just to check something quickly".
- **TETHER off.** Your Samsung is Persona A; BLE pairing leaks identity.
- **Different macOS user account** if your threat model warrants Level 2 (or use a VM / live USB).
- **No Persona-A files open** in the same session.
- **Different time-of-day patterns** than your Persona A use.
- **Different writing style** (see §1).

### Before each session

Ask: "Is anything from Persona A reachable from this session right now?" If yes, close it first.

### After each session

Tor Browser clears most state automatically, but check anyway:
- Downloads folder — wipe anything from this session
- Clipboard — clear it
- Any apps that were opened during the session — close them
- Recent files lists — clear in any app you used

---

## 5. Physical-presence discipline

CHIMERA's TETHER and screen lock defend the machine when you leave. They do NOT defend it when you are present but distracted.

- **In public:** orient the screen away from cameras, walls, mirrors.
- **In coffee shops and shared spaces:** use a privacy screen film. It is cheap and works.
- **Sensitive typing:** shield with body. Never face a camera or window when entering an override phrase.
- **Sleep mode is not lock.** Close the lid or lock explicitly when standing up.
- **Trust your machine more than the room you are in, never the reverse.**

---

## 6. Travel and border crossings

If your work involves travel through unpredictable or hostile zones, separate practices apply.

### Before travel

- Review PURGE Tier-2 targets. Consider crypto-shredding non-essential vaults preemptively.
- Decide whether the trip warrants a clean travel laptop (see below).
- Practice the panic gesture once before departure.

### The travel-laptop principle

The laptop you carry across a border is NOT the laptop you work on. A travel laptop is:
- A fresh install, no CHIMERA secrets
- No real-name accounts logged in
- Expendable — if seized, you lose nothing irreplaceable
- Reimaged or destroyed after return if it left your sight

This is a separate physical device. Wiping your main laptop before travel does not provide the same guarantee — forensic recovery of recent state is possible.

### At the crossing

- Devices powered OFF, not asleep, not "just locked".
- Be prepared to be compelled to unlock; assume any compelled access means full compromise.
- Whatever the outcome, behave as though they imaged the disk.

### After return

Any device that left your sight is potentially compromised. Treat its state as suspect until verified — fresh install before trusting it again.

---

## 7. Operational tempo and fatigue

PULSE will gate destructive actions when you are tired. Help PULSE help you:

- Do not arm PURGE for the first time at 3 am.
- Do not change CHIMERA configuration during a stressful event.
- Do not respond to "urgent" requests via Persona B without sleep first.
- Do not re-evaluate the threat model under emotional load. Note the impulse, revisit when calm.

If PULSE blocks you, take that seriously. It is right more often than you are at 0.9 score.

---

## 8. Information you must keep ONLY in your head

Never write down, never type into any digital system, never tell anyone:

- The master phrase used for each system (VAULT, PURGE, TETHER, PULSE override)
- The exact PURGE arming state at any given moment
- The current contents of the Tier-2 destruction list
- Which persona you used for which task
- Whether you maintain an "always-armed PURGE" configuration or not
- The location of any paper backup of any phrase

Anything in this list, if compromised, breaks the security model. Anything NOT in this list can live in your filesystem (encrypted) and you will be fine.

If you find yourself wanting to write one of these down "just to remember", that is the moment to type-practice it five times instead.

---

## 9. Quarterly self-review

Every three months, deliberately and manually — no script reminders:

- Re-read this document. Edit anything that no longer matches your actual practice.
- Re-read ARCHITECTURE.md §8 invariants. Are they still respected in how you use the system?
- Run `purge.test` for each armed configuration.
- Rotate any override phrase you typed on a borderline-trusted machine in the last quarter.
- Verify TETHER companion pairing still resolves correctly.
- Verify CHIMERA Keychain entries are healthy.
- Confirm the persona separation is intact — no slips, no "just this once" exceptions accumulated.

If you skipped two consecutive quarterly reviews, treat the system as out of discipline until a full review completes. Lock down, do not pretend the system is healthy.

The review is manual on purpose. A script that nags you reduces this to clicking through; an internalized rhythm that you keep yourself is the discipline.

---

## 10. Honest limits

This document is not a security guarantee. It is a discipline.

You will fail at some of these rules. CHIMERA is designed to fail gracefully when you do — secrets fail closed (a mistake never opens a vault or unpauses traffic), while the cognitive gate fails open (a broken fatigue sensor never locks you out of your own machine); and the dependency cascade can only lock more, never destroy (ARCHITECTURE I3, I4).

The goal is not perfection. It is making the cost of a mistake bounded and recoverable for as many mistakes as possible — and making the few unrecoverable ones (forgotten phrases, mixed personas) explicit, so you know exactly which lines truly cannot be crossed.

Discipline is the layer below the architecture. Without it, the architecture is decoration.

---

## Open questions

These are unresolved and will evolve with practice:

- **Travel-laptop spec.** What does a "clean travel machine" actually look like — hardware, OS, network setup?
- **Persona-B writing style.** Practical techniques for not leaking stylometry: drafting in another language, AI rewriting, lexical filters?
- **Override-phrase practice mechanism.** Weekly drill how — paper card you re-read, an encrypted note you re-type, a memory palace technique?
- **Panic-gesture choice.** Power-button pattern vs hotkey-hold vs hardware dongle — what are the operator-relevant trade-offs?
- **Quarterly review framing.** Should there be a written log of each review (for your own continuity) or strictly nothing on disk?

---

## Status

Living document. v1.0. Will evolve with practice.
Read in conjunction with: MANIFESTO.md, ARCHITECTURE.md §8, STATE.md.

No imitations. No theater. (See MANIFESTO §4.)
