"""Mapping from model label spaces into the app's Uzbek vocabulary.

The disease model (kimcomehome/plantvillage-vit-leaf-disease) is trained on
PlantVillage and emits 38 English `Crop___Disease` labels.

NOTE: the Uzbek disease names below are translations written without
agronomist review, same caveat as data/plants.json. Have them checked before
the app is used for real advice.
"""

HEALTHY = "Sog'lom"

# plants.json id -> the crop prefix used by the PlantVillage label space.
# Only these four of our eight crops are covered by the disease model.
CROP_BY_PLANT_ID = {
    "tomato": "Tomato",
    "potato": "Potato",
    "apple": "Apple",
    "grape": "Grape",
}

# Exact PlantVillage label -> Uzbek. Keys must match the model config verbatim.
DISEASE_UZ = {
    "Apple___Apple_scab": "Olma qo'tiri",
    "Apple___Black_rot": "Qora chirish",
    "Apple___Cedar_apple_rust": "Olma zangi",
    "Apple___healthy": HEALTHY,
    "Grape___Black_rot": "Qora chirish",
    "Grape___Esca_(Black_Measles)": "Eska (qora o'lat)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": "Barg kuyishi",
    "Grape___healthy": HEALTHY,
    "Potato___Early_blight": "Alternarioz (erta kuyish)",
    "Potato___Late_blight": "Fitoftoroz (kech kuyish)",
    "Potato___healthy": HEALTHY,
    "Tomato___Bacterial_spot": "Bakterial dog'lanish",
    "Tomato___Early_blight": "Alternarioz (erta kuyish)",
    "Tomato___Late_blight": "Fitoftoroz (kech kuyish)",
    "Tomato___Leaf_Mold": "Barg mog'ori",
    "Tomato___Septoria_leaf_spot": "Septorioz",
    "Tomato___Spider_mites Two-spotted_spider_mite": "O'rgimchakkana",
    "Tomato___Target_Spot": "Nishonsimon dog'",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Sariq barg burishish virusi",
    "Tomato___Tomato_mosaic_virus": "Tamaki mozaikasi virusi",
    "Tomato___healthy": HEALTHY,
}

# English CLIP prompts per plants.json id. CLIP is English-trained, so the
# Uzbek names in plants.json cannot be used as prompts directly.
#
# Keep these BALANCED across crops: every crop gets a whole-plant prompt, a
# leaf prompt and a bare-fruit/product prompt. An asymmetry here shows up as a
# systematic error - while building this, tomato had a bare-fruit prompt and
# apple did not, and a studio photo of a red apple was confidently called a
# tomato.
SPECIES_PROMPTS = {
    "tomato": [
        "a tomato plant",
        "tomato plant leaves",
        "a ripe red tomato fruit on a plain background",
    ],
    "cotton": [
        "a cotton plant",
        "cotton plant leaves",
        "an open white cotton boll",
    ],
    "grape": [
        "a grape vine",
        "grape vine leaves",
        "a bunch of grapes on a plain background",
    ],
    "apple": [
        "an apple tree",
        "apple tree leaves",
        "a single red apple fruit on a plain background",
    ],
    "wheat": [
        "a wheat plant",
        "a field of wheat",
        "ears of wheat grain",
    ],
    "pomegranate": [
        "a pomegranate tree",
        "pomegranate tree leaves",
        "a whole pomegranate fruit on a plain background",
    ],
    "apricot": [
        "an apricot tree",
        "apricot tree leaves",
        "whole apricot fruits on a plain background",
    ],
    "potato": [
        "a potato plant",
        "potato plant leaves",
        "raw potato tubers on a plain background",
    ],
}

# If one of these wins, the photo is not one of our crops and the UI should say
# so rather than naming the closest plant. Without them CLIP always picks a
# crop, because softmax over eight crops has nowhere else to put the mass.
DISTRACTOR_PROMPTS = [
    "a person",
    "an animal",
    "a car",
    "a building",
    "a computer or phone screen",
    "a piece of furniture",
    "a cooked meal on a plate",
    "a document or text on paper",
    "an unrelated houseplant",
    "a flower that is not a crop",
    "a blurry photo of nothing in particular",
]

# The disease model was trained on single leaves against a plain background.
# On whole-plant, fruit or field photos it still returns a confident answer,
# and that answer is usually wrong - so we check how leaf-like the photo is
# first and refuse to make a specific claim when it is not.
LEAF_PROMPTS = [
    "a close-up photo of a single plant leaf",
    "a close-up photo of plant leaves filling the frame",
    "a plant leaf photographed against a plain background",
]

NOT_LEAF_PROMPTS = [
    "a photo of a whole plant or tree",
    "a wide photo of a field or landscape",
    "a photo of a harvested fruit or vegetable",
    "a photo of flowers",
    "a photo of soil or ground",
]

# Binary prompts used for crops the disease model does not cover.
HEALTH_PROMPTS = {
    HEALTHY: [
        "a healthy green {plant} leaf",
        "a {plant} plant with no disease",
    ],
    "Kasallik belgilari bor": [
        "a diseased {plant} leaf with brown spots",
        "a {plant} plant with yellowing wilting damaged leaves",
    ],
}
