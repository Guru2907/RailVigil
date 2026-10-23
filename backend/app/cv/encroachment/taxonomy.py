"""RailVigil's encroachment classes and how model labels map onto them.

Only labels listed here can become encroachment detections; everything else a
model sees is ignored. `Train` is deliberately absent: a train on railway land
is not an encroachment.
"""

STRUCTURE_PERMANENT = "structure_permanent"
STRUCTURE_TEMPORARY = "structure_temporary"
VEGETATION = "vegetation"
DEBRIS_WASTE = "debris_waste"
MATERIAL_DUMP = "material_dump"
VEHICLE_PARKED = "vehicle_parked"

CLASSES = (
    STRUCTURE_PERMANENT,
    STRUCTURE_TEMPORARY,
    VEGETATION,
    DEBRIS_WASTE,
    MATERIAL_DUMP,
    VEHICLE_PARKED,
)

# Open Images V7 label -> class (model "oiv7-v8s").
OIV7_LABELS = {
    "House": STRUCTURE_PERMANENT,
    "Building": STRUCTURE_PERMANENT,
    "Office building": STRUCTURE_PERMANENT,
    "Skyscraper": STRUCTURE_PERMANENT,
    "Tower": STRUCTURE_PERMANENT,
    "Tent": STRUCTURE_TEMPORARY,
    "Tree house": STRUCTURE_TEMPORARY,
    "Tree": VEGETATION,
    "Palm tree": VEGETATION,
    "Plant": VEGETATION,
    "Car": VEHICLE_PARKED,
    "Truck": VEHICLE_PARKED,
    "Van": VEHICLE_PARKED,
    "Bus": VEHICLE_PARKED,
    "Motorcycle": VEHICLE_PARKED,
    "Cart": VEHICLE_PARKED,
    "Land vehicle": VEHICLE_PARKED,
    "Vehicle": VEHICLE_PARKED,
}

# YOLO-World text prompt -> class (model "world-v8s-railvigil"). These prompts
# are baked into the model by scripts/build_world_model.py; changing this dict
# means rebuilding that model.
WORLD_PROMPTS = {
    "hut": STRUCTURE_TEMPORARY,
    "shack": STRUCTURE_TEMPORARY,
    "tin shed": STRUCTURE_TEMPORARY,
    "tarpaulin shelter": STRUCTURE_TEMPORARY,
    "roadside stall": STRUCTURE_TEMPORARY,
    "kiosk": STRUCTURE_TEMPORARY,
    "concrete building": STRUCTURE_PERMANENT,
    "brick wall": STRUCTURE_PERMANENT,
    "garbage pile": DEBRIS_WASTE,
    "trash heap": DEBRIS_WASTE,
    "scrap metal pile": DEBRIS_WASTE,
    "construction debris": DEBRIS_WASTE,
    "pile of bricks": MATERIAL_DUMP,
    "sand pile": MATERIAL_DUMP,
    "construction material": MATERIAL_DUMP,
    "bush": VEGETATION,
    "overgrown vegetation": VEGETATION,
    # Without these, YOLO-World labelled parked auto-rickshaws "roadside stall".
    "auto rickshaw": VEHICLE_PARKED,
    "cycle rickshaw": VEHICLE_PARKED,
}

# Distractor prompts: legitimate railway things and people. YOLO-World gives
# each box the best-matching prompt, so offering these lets look-alikes (a
# platform shelter, a concrete kerb) land here instead of on an encroachment
# prompt. They map to no class and never become findings.
WORLD_DISTRACTORS = (
    "train",
    "railway platform",
    "platform shelter",
    "railway signal",
    "concrete kerb",
    "person",
)

# Order of the prompts baked into the YOLO-World model.
WORLD_MODEL_PROMPTS = (*WORLD_PROMPTS, *WORLD_DISTRACTORS)

LABEL_MAPS = {
    "oiv7-v8s": OIV7_LABELS,
    "world-v8s-railvigil": WORLD_PROMPTS,
    # The trained model's classes are RailVigil's own classes.
    "railvigil-seg": {c: c for c in CLASSES},
}


def map_label(model_name: str, label: str) -> str | None:
    """Our class for a model's label, or None if the label is not relevant."""
    return LABEL_MAPS.get(model_name, {}).get(label)
