# Sample Story 1: The Diner Meeting

**Purpose:** Minimal test case for canon extraction

---

Fox enters the diner, scanning the room. He's wearing his signature leather jacket - worn, comfortable, the kind that's seen better days.^ev_a1b2

Sarah's already in the back booth. She's got a manila folder in front of her, fingers drumming on the table.^ev_c3d4

FOX walks over, slides into the booth opposite her.^ev_e5f6

FOX: You're early.^ev_g7h8

SARAH: So are you.^ev_i9j0

She slides the folder across. Fox doesn't open it.^ev_k1l2

FOX: What's in the folder, Sarah?^ev_m3n4

SARAH: The lighthouse. Everything about the drop.^ev_o5p6

Fox goes still. He hadn't expected her to know about that.^ev_q7r8

---

## Expected Extractions

### Characters
- CHAR_Fox (aliases: FOX)
- CHAR_Sarah (aliases: SARAH)

### Locations
- LOC_Diner (the diner, back booth)

### Props
- PROP_Manila_Folder (the folder, manila folder)
- PROP_Leather_Jacket (his jacket, signature jacket)

### Scenes
- SCN_001: INT. DINER - (time unknown)

### Knowledge Events
- SARAH knows about "the lighthouse drop"
- FOX didn't expect SARAH to know
- Potential KNOW-01 issue: When did Sarah learn about the lighthouse?
